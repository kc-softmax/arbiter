import pygame
import math
import gymnasium as gym
import numpy as np
import gymnasium.spaces as spaces
import uuid
import asyncio
from gymnasium.utils import seeding
from collections import defaultdict
from typing import List, Any, Tuple, Type
from maenv.dusty.dusty_agent import DustyAgent
from maenv.dusty.dusty_map import DustyMap
from maenv.dusty.utils import get_distance
from maenv.dusty.enums import (
    DustyActiveAction,
    DustyControlAction,
    DustyState,
    DeathType,
    RewardType,
    Equipment,
    CollideType,
    PygameRenderMode,
    Team
)
from maenv.dusty.colors import (
    WHITE, BLUE, ORANGE, YELLOW_DUSTY_GRID, BLUE_DUSTY_GRID
)
from maenv.dusty.collisions import Collision
from maenv.dusty.dataclasses import DustyGameConfig, DustyStepConfig, DustyMapConfig
from maenv.dusty.game_objects import (
    Energy,
    Explosion,
    Bullet,
)
from maenv.dusty.dusty_log_manager import DustyLogManager


class DustyEnv(gym.Env):

    def __init__(
        self,
        agent_ids: List[str] = [],
        step_rate: int = 10,
        seed=927,
        logging=True,
        game_config: dict[str, Any] = {},
        step_config: dict[str, Any] = {},

    ) -> None:
        super(DustyEnv, self).__init__()
        self.room_id = str(uuid.uuid4())
        self.np_random = None
        self.options = None

        self.seed(seed=seed)
        self.map_config = DustyMapConfig()
        self.game_config = DustyGameConfig(
            **game_config, map_config=self.map_config)
        self.step_config = DustyStepConfig(step_rate=step_rate, **step_config)
        self.step_count: int = 0
        # address: occupier_id
        # because of using dict, avoid address dupliction
        self.blue_scores: dict[int: str] = defaultdict(str)
        self.yellow_scores: dict[int: str] = defaultdict(str)

        self.logging = logging
        self.logs: DustyLogManager = DustyLogManager()

        self.agents: dict[str, DustyAgent] = {}
        self.removing_agents: List[DustyAgent] = []

        self.bullets: List[Bullet] = []
        self.removing_bullets: List[Bullet] = []
        self.explosions: List[Explosion] = []

        self.map = DustyMap(self.np_random, self.game_config.map_config)
        self.in_grid_energy_objects: dict[int, List[Energy]] = {}
        self.max_energy_count: int = math.floor(
            self.map.grid_rows * self.map.grid_cols * self.map.grid_scale * 0.4)
        self.energies: List[Energy] = []
        self.removing_energies: List[Energy] = []

        self.observation_shape = (96, 96, 3)
        self.observation_space = spaces.Box(
            low=0,
            high=255,
            shape=self.observation_shape,
            dtype=np.uint8
        )
        self.action_space = spaces.Discrete(9)
        self.actions = {}

        for agent in self.generate_agents(agent_ids):
            self.add_agent(agent)
        self.reset()

    def find_possible_state_area(self, x: int, y: int) -> tuple[int, int, int, int]:
        '''This function is for finding possible state area
        
        Args:
            x (int): dusty's x position
            y (int): dusty's y position
            
        Returns:
            tuple: (start_x, end_x, start_y, end_y)
        
        '''
        start_x = x - self.observation_shape[0] // 2
        end_x = x + self.observation_shape[1] // 2
        start_y = y - self.observation_shape[0] // 2
        end_y = y + self.observation_shape[1] // 2
        if start_x < 0:
            start_x = 0
            end_x = self.observation_shape[0]
        if end_x > self.game_config.map_config.grid_width:
            start_x = self.game_config.map_config.grid_width - self.observation_shape[0]
            end_x = self.game_config.map_config.grid_width
        if start_y < 0:
            start_y = 0
            end_y = self.observation_shape[1]
        if end_y > self.game_config.map_config.grid_height:
            start_y = self.game_config.map_config.grid_height - self.observation_shape[1]
            end_y = self.game_config.map_config.grid_height
        return (start_x, end_x, start_y, end_y)

    # def add_agent(self, agent: DustyAgent) -> None:
    #     if agent.id in self.agents:
    #         raise Exception(f"Agent {agent.id} already exists")
    #     agent.set_config(self.game_config, self.step_config)
    #     self.agents[agent.id] = agent
    #     self.reset_agent(agent)

    def add_agent(self, user_id: str, team: int) -> None:
        if user_id in self.agents:
            raise Exception(f"Agent {user_id} already exists")
        agent = DustyAgent(user_id, team)
        agent.set_config(self.game_config, self.step_config)
        self.agents[agent.id] = agent
        self.reset_agent(agent)

    def generate_agents(self, agent_ids: List[str]) -> List[DustyAgent]:
        agents: List[DustyAgent] = []
        blue_count = 0
        yellow_count = 0
        for agent in self.agents.values():
            match agent.team:
                case Team.BLUE:
                    blue_count += 1
                case Team.YELLOW:
                    yellow_count += 1
        # override this function to generate custom agents
        for agent_id in agent_ids:
            if agent_id in self.agents:
                raise Exception('agent id already exists')

            # team distribution
            team = Team.BLUE if blue_count <= yellow_count else Team.YELLOW
            match team:
                case Team.BLUE:
                    blue_count += 1
                case Team.YELLOW:
                    yellow_count += 1
            agent = DustyAgent(agent_id, team)
            agent.set_config(self.game_config, self.step_config)
            agents.append(agent)
        return agents

    def reset_agent(self, agent: DustyAgent) -> None:
        starting_point = self.map.get_respwan_points(agent.team, 1)[0]
        agent.reset(starting_point, self.np_random)

    def add_energy_grid_info(self, energy: Energy) -> None:
        grid_index = self.map.get_grid_index_by_location(
            energy.centerx, energy.centery)
        if grid_index is None or grid_index not in self.in_grid_energy_objects:
            return
        self.in_grid_energy_objects[grid_index].append(energy)

    def remove_energy_grid_info(self, energy: Energy) -> None:
        grid_index = self.map.get_grid_index_by_location(
            energy.centerx, energy.centery)
        if grid_index is None or grid_index not in self.in_grid_energy_objects:
            return
        # 지우는 순서 확인해야 한다.
        try:
            self.in_grid_energy_objects[grid_index].remove(energy)
        except Exception as exp:
            print(exp)

    # def remove_agent(self, agent: DustyAgent) -> None:
    #     if self.logging:
    #         self.logs.removeDusty(agent)
    #     del self.agents[agent.id]

    def remove_agent(self, user_id: str) -> None:
        if self.logging:
            agent = self.agents[user_id]
            self.logs.removeDusty(agent)
        del self.agents[user_id]

    def respwan_energy(self):
        energy_count = len(self.energies)
        if energy_count < self.max_energy_count:
            generate_energy_count = self.max_energy_count - energy_count
            if generate_energy_count > self.game_config.max_energy_in_step:
                generate_energy_count = self.game_config.max_energy_in_step
            energy_points = [
                (points[0], points[1])
                for points in self.map.get_random_points(generate_energy_count)
            ]
            self.generate_energy(energy_points)

    def generate_energy(self, energy_points: list[Tuple[int, int]]):
        for point in energy_points:
            energy = Energy(
                point[0],
                point[1],
                self.game_config.default_object_size
            )            # TODO refactor
            self.energies.append(energy)
            if self.logging:
                self.logs.addEnergy(energy)
            self.add_energy_grid_info(energy)

    # TODO change name to like casting skill
    def fire_bullet(self, agent: DustyAgent) -> None:
        diagonal = (agent.body.width ** 2 +
                    agent.body.height ** 2) ** 0.5

        bullet_x = math.ceil(agent.body.centerx +
                             agent.direction[0] * diagonal * 1)

        bullet_y = math.ceil(agent.body.centery +
                             agent.direction[1] * diagonal * 1)

        match agent.equipment:
            case Equipment.SHOTGUN:
                bullet_size = self.game_config.shotgun_bullet_size
                bullet_stride = self.game_config.shotgun_bullet_stride
            case Equipment.GUIDED:
                bullet_size = self.game_config.guided_bullet_size
                bullet_stride = self.game_config.guided_bullet_stride
            case Equipment.REMOVER:
                bullet_size = self.game_config.remover_bullet_size
                bullet_stride = self.game_config.remover_bullet_stride
            case _:
                bullet_size = self.game_config.bullet_size
                bullet_stride = self.game_config.bullet_stride
        if agent.equipment == Equipment.SHOTGUN:
            bullet_direction = agent.direction.rotate_rad(
                self.game_config.shotgun_bullet_count // 2 *
                self.game_config.shotgun_bullet_angle * -1
            )
            for _ in range(self.game_config.shotgun_bullet_count):
                bullet = Bullet(
                    bullet_x,
                    bullet_y,
                    bullet_direction,
                    agent.id,
                    agent.team,
                    self.step_count,
                    bullet_size,
                    bullet_stride,
                    Equipment.SHOTGUN)
                bullet_direction = bullet_direction.rotate_rad(
                    self.game_config.shotgun_bullet_angle)
                if self.logging:
                    self.logs.addBullet(bullet)
                self.bullets.append(bullet)
        else:
            bullet = Bullet(
                bullet_x,
                bullet_y,
                agent.direction,
                agent.id,
                agent.team,
                self.step_count,
                bullet_size,
                bullet_stride,
                agent.equipment)
            if self.logging:
                self.logs.addBullet(bullet)

            self.bullets.append(bullet)

        # 멀티샷이든 한발로 생각한다.
        agent.score.firing_count += 1

    def remove_bullet(self, bullet: Bullet) -> None:
        if self.logging:
            self.logs.removeBullet(bullet)
        if bullet in self.bullets:
            self.bullets.remove(bullet)

    def remove_energy(self, energy: Energy) -> None:
        self.remove_energy_grid_info(energy)
        if self.logging:
            self.logs.removeEnergy(energy)
        if energy in self.energies:
            self.energies.remove(energy)

    def check_collisions(self, **kwargs) -> List[Collision]:
      # if you want custom collisions, override this function
        # 여기서는 pygame으로 전부 검사한다.
        collisions: List[Collision] = []
        dusty_agents: List[DustyAgent] = self.agents.values()
        large_grids = self.map.large_grids

        # 만약 폭탄이 터진 후 그자리에 폭팔염? 장판이 있는걸 고려해야 한다.
        # 장판은 그리드 오브젝트로 추가하여 agent를 검사할때 처리
        for bullet in self.bullets:
            is_guided = bullet.bullet_type == Equipment.GUIDED
            if bullet.left < 0 or bullet.right > self.map.map_width:
                # bullet destoryed, out of grid
                collisions.append(
                    Collision(src=bullet))
                bullet.collide_type = CollideType.OUT_OF_GRID
                continue
            if bullet.shooter not in self.agents:
                # bullet destoryed, shooter is quit
                collisions.append(
                    Collision(src=bullet))
                bullet.collide_type = CollideType.DISAPPEAR
                continue
            # guided bullet destoryed, when target is None or not alive
            if is_guided and bullet.lock_on:
                if bullet.target_id not in self.agents or not self.agents[bullet.target_id].alive:
                    bullet.release_target()

            shooter_agent = self.agents[bullet.shooter]

            for agent in dusty_agents:
                if not agent.alive:
                    continue

                colleague_bullet = bullet.team == agent.team
                shooter_bullet = bullet.shooter == agent.id

                # if shooter_agent:
                #     continue

                if not shooter_bullet and not bullet.lock_on and is_guided:
                    if not colleague_bullet:
                        # 같은팀이 쏜 총알이 아닐경우
                        dist = get_distance(bullet, agent.body)
                        # guided_distance todo const
                        if dist < self.map.grid_width:
                            bullet.set_target(agent.id, agent.body.center)
                            self.logs.updateBullet(bullet)

                bullet.target_id == agent.id and bullet.update_target(
                    agent.body.center)

                if bullet.colliderect(agent.body):
                    if agent.state == DustyState.FREEZE:
                        # freeze - 무적 상태일때, 죽이지는 못하고 그냥 터짐
                        collisions.append(
                            Collision(src=bullet))
                        bullet.collide_type = CollideType.AGENT
                        continue

                    # 우리팀일때랑 상대팀일때랑 차등
                    if colleague_bullet:
                        # energy
                        collisions.append(
                            Collision(src=bullet, agent=agent))
                        bullet.collide_type = CollideType.COLLEAGUE
                    else:
                        collisions.append(
                            Collision(src=bullet, agent=agent))
                        bullet.collide_type = CollideType.AGENT

            collide_grid_object_ids = bullet.collidelistall(large_grids)

            collide_bullet_object_ids = bullet.collidelistall(self.bullets)

            for collide_index in collide_bullet_object_ids:
                collide_bullet = self.bullets[collide_index]
                if bullet.id == collide_bullet.id:
                    continue

                if collide_bullet.shooter in self.agents:
                    other_shooter_agent = self.agents[collide_bullet.shooter]
                    colleague_bullet = shooter_agent.team == other_shooter_agent.team
                else:
                    colleague_bullet = False

                # 이하 로직은 본인이 쏜 총알들 끼리의 충돌이므로, 특수한 경우가 아니면 무시한다.
                if bullet.shooter == collide_bullet.shooter:
                    continue

                if (
                    not colleague_bullet and
                    get_distance(shooter_agent.body, collide_bullet) < self.game_config.bullet_defence_distance and
                    collide_bullet.generate_step < bullet.generate_step  # 나중에 발사된거여만
                ):
                    # 요격에 성공
                    collisions.append(
                        Collision(
                            src=bullet,
                            game_object=collide_bullet))
                    bullet.collide_type = CollideType.DEFENCE
                else:
                    collisions.append(
                        Collision(
                            src=bullet,
                            game_object=collide_bullet))
                    bullet.collide_type = CollideType.BULLET
                # 그냥 다른곳에서 터짐

            for collide_grid_index in collide_grid_object_ids:
                grid = large_grids[collide_grid_index]

                if grid.collide_trees(bullet):
                    collisions.append(
                        Collision(src=bullet))
                    bullet.collide_type = CollideType.TREE

                if grid.unused:
                    collisions.append(
                        Collision(src=bullet))
                    bullet.collide_type = CollideType.DISAPPEAR
                # remover bullet 일때
                elif bullet.bullet_type == Equipment.REMOVER:
                    collide_middle_grid_indexes = bullet.collidelistall(
                        grid.child_grids)
                    for index in collide_middle_grid_indexes:
                        middle_grid = grid.child_grids[index]
                        if not middle_grid.occupier_team:
                            continue
                        if middle_grid.address in self.yellow_scores:
                            self.yellow_scores.pop(middle_grid.address)
                        if middle_grid.address in self.blue_scores:
                            self.blue_scores.pop(middle_grid.address)
                        middle_grid.reset(True)
                        self.logs.changeGrid(middle_grid)

            if not collide_grid_object_ids:
                # bullet destoryed, out of grid
                collisions.append(
                    Collision(src=bullet))
                bullet.collide_type = CollideType.DISAPPEAR

        for agent in dusty_agents:
            if not agent.alive:
                continue

            if agent.body.left < 0 or agent.body.right > self.map.map_width:
                agent.handle_collision_with_obstacle()

            if agent.foot:
                # 발이 생성된 agent의 경우 체크한다.
                # 시작 후 freeze 상태일때는 발이 없다.
                collide_grids = agent.foot.collidelistall(large_grids)
                for grid_index in collide_grids:
                    grid = large_grids[grid_index]
                    if grid.unused:
                        # 사용못하는 그리드
                        agent.handle_collision_with_obstacle(grid)
                    else:
                        # 사용하는 그리드 그 안에 그리드랑 검사한다
                        # 있는 그리드 다 검사해야 한다.
                        if agent.state != DustyState.FREEZE:
                            collide_middle_grid_indexes = agent.foot.collidelistall(
                                grid.child_grids)

                            for middle_grid_idx in collide_middle_grid_indexes:
                                # 땅의 주인이 된다.
                                middle_grid = grid.child_grids[middle_grid_idx]

                                if middle_grid.occupier_team == agent.team:
                                    continue

                                collisions.append(
                                    Collision(src=agent, middle_grid=middle_grid))

                        in_grid_energies = self.in_grid_energy_objects[grid_index]

                        collide_energy_ids = agent.body.collidelistall(
                            in_grid_energies)
                        for collide_energy_id in collide_energy_ids:
                            collisions.append(
                                Collision(
                                    src=agent,
                                    game_object=in_grid_energies[collide_energy_id]
                                ))

                        # 나무에 부딪힘
                        collided_trees = grid.collide_trees(agent.foot)
                        if collided_trees:
                            for collided_tree in collided_trees:
                                agent.handle_collision_with_obstacle(
                                    collided_tree)

            # check collisions with other agents
            for other_agent in dusty_agents:
                if not other_agent.alive:
                    continue
                if other_agent.id == agent.id:
                    continue
                if agent.body.colliderect(other_agent.body):
                    if other_agent.state == DustyState.FREEZE:
                        # 무적 상태에 부딪혔을대는
                        agent.handle_collision_with_obstacle()
                    elif agent.team == other_agent.team:
                        agent.handle_collision_with_obstacle()
                    else:
                        collisions.append(
                            Collision(src=agent, agent=other_agent))

        # explosion을 체크한다
        while self.explosions:
            explosion = self.explosions.pop()
            # 폭탄의 종류에 따라서 충돌 검사
            # 현재는 페인트 벌룬만 생각
            collide_grid_indexes = explosion.collidelistall(large_grids)
            for grid_index in collide_grid_indexes:
                grid = large_grids[grid_index]
                if grid.unused:
                    continue
                collide_middle_grid_indexes = explosion.collidelistall(
                    grid.child_grids)
                for middle_grid_idx in collide_middle_grid_indexes:
                    # 땅의 주인이 된다.
                    middle_grid = grid.child_grids[middle_grid_idx]
                    if middle_grid.occupier_team == explosion.team:
                        continue
                    if middle_grid.used:
                        continue
                    if not middle_grid.occupyable:
                        continue
                    collisions.append(
                        Collision(src=explosion, middle_grid=middle_grid))

        return collisions

    def collision_processing(
        self,
        collisions: List[Collision]
    ) -> None:
        for collision in collisions:
            if isinstance(collision.src, DustyAgent):
                self.handle_agent_collide(collision)
            if isinstance(collision.src, Bullet):
                self.handle_bullet_collide(collision)
            if isinstance(collision.src, Explosion):
                self.handle_explosion_collide(collision)

    def handle_fight_result(
        self,
        losers: List[DustyAgent],
        winner: DustyAgent = None,
    ) -> None:
        for loser in losers:
            loser.die(DeathType.AGENT)
            loser.killer = winner
            loser.score.death += 1
            if winner and winner.id != loser.id:
                winner.earn_reward(RewardType.KILLING)

    def handle_explosion_collide(self, collision: Collision) -> None:
        # TODO 무언가 할 수 있을것 같다.
        explosion: Explosion = collision.src
        bomber: DustyAgent = self.agents[explosion.bomber] if explosion.bomber in self.agents else None
        if collision.middle_grid:
            middle_grid = collision.middle_grid
            if middle_grid.occupyable and not middle_grid.used:
                # TODO export function? or charge change to agent?
                bomber and bomber.earn_reward(RewardType.PAINTING)
                middle_grid.occupier_id = explosion.bomber
                middle_grid.occupier_team = explosion.team
                self.logs.changeGrid(middle_grid)
                match explosion.team:
                    case Team.BLUE:
                        if middle_grid.address in self.yellow_scores:
                            self.yellow_scores.pop(middle_grid.address)
                        # TODO change
                        self.blue_scores[middle_grid.address] = explosion.bomber
                    case Team.YELLOW:
                        if middle_grid.address in self.blue_scores:
                            self.blue_scores.pop(middle_grid.address)
                        self.yellow_scores[middle_grid.address] = explosion.bomber
            else:
                # 모종의 이유로 점령 불가능한 지역이다. (황폐화)
                pass

    def handle_bullet_collide(self, collision: Collision) -> None:
        bullet: Bullet = collision.src
        # 쏘고 나가고 나서 충돌이 일어난다. (총알을 제거하기 전)
        shooter_agent = self.agents[bullet.shooter] if bullet.shooter in self.agents else None

        # 각 총알마다 차이를 둬야 할지도? 어떤 방법이 좋을까
        if collision.game_object:
            if isinstance(collision.game_object, Energy):  # 현재는 사용하지 않는다
                # 총알과 에너지가 부딪힌다면?, 에너지 영역을 페인트?
                pass
            elif isinstance(collision.game_object, Bullet):
                # TODO export function?
                if (
                    shooter_agent and
                    bullet.collide_type == CollideType.DEFENCE
                ):
                    shooter_agent.earn_reward(RewardType.DEFENCE)  # 총알을 막았다
        # TODO refactor
        elif collision.agent and collision.agent.alive:

            # 동료가 쏜거에 맞아도 죽는다.
            # collision.agent.earn_energy(1)
            # else:
            if bullet.shooter in self.agents:
                winner = self.agents[bullet.shooter]
            else:
                winner = None
            losers = [collision.agent]
            self.handle_fight_result(losers, winner)

        self.removing_bullets.append(bullet)

    def handle_agent_collide(self, collision: Collision) -> dict[str, float]:

        agent: DustyAgent = collision.src

        if not agent.alive:
            return []

        if collision.large_grid:
            if collision.large_grid.unused:
                # agent의 이동을 취소한다.
                # 버그가 있네?
                agent.handle_collision_with_obstacle()
        if collision.middle_grid:
            middle_grid = collision.middle_grid
            if middle_grid.occupyable:
                # TODO export function? or charge change to agent?
                agent.earn_reward(RewardType.PAINTING)
                middle_grid.occupier_id = agent.id
                middle_grid.occupier_team = agent.team
                self.logs.changeGrid(middle_grid)
                match agent.team:
                    case Team.BLUE:
                        if middle_grid.address in self.yellow_scores:
                            self.yellow_scores.pop(middle_grid.address)
                        self.blue_scores[middle_grid.address] = agent.id
                    case Team.YELLOW:
                        if middle_grid.address in self.blue_scores:
                            self.blue_scores.pop(middle_grid.address)
                        self.yellow_scores[middle_grid.address] = agent.id
            else:
                # 모종의 이유로 점령 불가능한 지역이다. (황폐화)
                pass
        elif collision.game_object:
            # game object에 대한 충돌 처리
            if isinstance(collision.game_object, Energy):
                agent.earn_reward(RewardType.ENERGY)
                collision.game_object.acquirers.append(agent.id)
                self.removing_energies.append(collision.game_object)
        # TODO refactor
        elif collision.agent and collision.agent.alive:
            # 현재는 둘 다 죽는다.
            other_agent = collision.agent
            winner = None
            losers = [agent, other_agent]
            self.handle_fight_result(losers, winner)

    def get_observations(self):
        obs = {}
        for agent in self.agents.values():
            # if not agent.alive: continue
            obs[agent.id] = self.obs[agent.id]
        return obs

    def get_rewards(self) -> dict[str, float]:
        # TODO update or dataclass
        rewards: dict[str, float] = {}
        # for agent in self.agents.values():
        #     rewards[agent.id] = len(self.occupied_grids[agent.id])
        # rewards['blue_score_info'] = self.blue_scores
        # rewards['yellow_score_info'] = self.yellow_scores
        # rewards['max_grid_count'] = self.map.valid_grid_count
        for agent_id, agent in self.agents.items():
            if agent.team == Team.BLUE:
                rewards[agent_id] = self.blue_scores
            else:
                rewards[agent_id] = self.yellow_scores
        return rewards

    def get_infos(self) -> dict[str, Any]:
        infos: dict[str, list | dict] = {
            "agent": {},
            "bullet": [],
            "energies": [],
            "tree": [],
            "wall": []
        }
        # infos['remain_step'] = self.step_config.game_step - self.step_count
        
        # agent
        for agent_id, agent in self.agents.items():
            x, y = agent.body.x // self.map.grid_cols, agent.body.y // self.map.grid_rows
            infos["agent"][agent_id] = [x, y, agent.get_color()]
        
        # bullet
        for bullet in self.bullets:
            x, y = bullet.x // self.map.grid_cols, bullet.y // self.map.grid_rows
            infos["bullet"].append([x, y, bullet.get_color()])
        
        # energies
        for energy in self.energies:
            x, y = energy.x // self.map.grid_cols, energy.y // self.map.grid_rows
            infos["energies"].append([x, y, energy.get_color()])
        
        for grid in self.map.large_grids:
            if grid.unused:
                x, y = grid.x // self.map.grid_cols, grid.y // self.map.grid_rows
                infos["wall"].append([x, y, WHITE])
            else:
                for middle_grid in grid.child_grids:
                    if middle_grid.occupier_team:
                        x, y = middle_grid.x // self.map.grid_cols, middle_grid.y // self.map.grid_rows
                        color = BLUE_DUSTY_GRID if middle_grid.occupier_team == Team.BLUE else YELLOW_DUSTY_GRID
                        infos["wall"].append([x, y, color])

            for tree in grid.trees:
                x, y = tree.x // self.map.grid_cols, tree.y // self.map.grid_rows
                infos["tree"].append([x, y, tree.get_color()])
        return infos

    def get_initial_infos(self) -> dict[str, Any]:
        return {
            agent.id: {}
            for agent in self.agents.values()
        }

    def get_terminateds(self) -> dict[str, bool]:
        """
        Returns whether each agent is terminated or not.
        TODO set terminate condition
        TODO select a winner if the game is terminated
        currently, agent is terminated when max_steps is reached        
        """
        # terminate condition
        # game - max_steps, one team occupy half of the map
        # agent - hard death, out of game ()
        terminated = {
            agent.id: False
            for agent in self.agents.values()
        }

        blue_score = math.floor(
            len(self.blue_scores) / self.map.valid_grid_count * 100)
        yellow_score = math.floor(
            len(self.yellow_scores) / self.map.valid_grid_count * 100)

        if (
            blue_score > 50 or
            yellow_score > 50 or
            self.step_count >= self.step_config.game_step
        ):
            terminated['__all__'] = True
        else:
            terminated['__all__'] = False

        return terminated

    def get_truncateds(self) -> dict[str, bool]:
        """
        Returns whether each agent is truncated or not.
        TODO set truncate condition
        currently, agent is truncated when is dead
        """
        truncated = {
            agent.id: agent.get_truncated()
            for agent in self.agents.values()
        }

        # is possible?
        truncated['__all__'] = all(list(truncated.values()))

        return truncated

    def render(self, **kwargs):

        # currently only supports human mode (pygame)
        mode: str = kwargs.get('mode', PygameRenderMode.NORMAL)
        screen: pygame.Surface = kwargs.get('screen', None)

        # deprecated some moment
        # if mode != 'human' or not screen:
        #     raise Exception('only human mode is supported with pygame')

        display_width = kwargs.get('display_width', 900)
        display_height = kwargs.get('display_height', 900)
        
        self.obs = {
            agent_id: np.zeros(self.observation_shape, dtype=np.uint8)
            for agent_id in self.agents
        }

        # TODO refactor
        if mode == PygameRenderMode.COMPRESS:
            surface = self.map.get_compressed_surface()
            for dusty_agent in self.agents.values():
                if dusty_agent.alive:
                    col, row = self.map.get_grid_address(
                        dusty_agent.body.x, dusty_agent.body.y)

                    pygame.draw.line(
                        surface, WHITE,
                        (col, row), pygame.math.Vector2(col, row) + dusty_agent.direction * 1.5, 1)

                    pygame.draw.line(
                        surface, WHITE,
                        (col, row), (col + 0.5, row + 0.5), 1)

                    pygame.draw.rect(
                        surface,
                        dusty_agent.get_color(),
                        pygame.Rect(
                            col,
                            row,
                            1, 1)
                    )

            for bullet in self.bullets:
                col, row = self.map.get_grid_address(
                    bullet.x, bullet.y)
                pygame.draw.rect(
                    surface,
                    bullet.get_color(),
                    pygame.Rect(
                        col,
                        row,
                        1, 1)
                )

            for energy in self.energies:
                col, row = self.map.get_grid_address(
                    energy.x, energy.y)
                pygame.draw.rect(
                    surface,
                    energy.get_color(),
                    pygame.Rect(
                        col,
                        row,
                        1, 1)
                )
        else:
            surface = self.map.get_surface()
            for dusty_agent in self.agents.values():
                if dusty_agent.alive:
                    pygame.draw.rect(
                        surface, dusty_agent.get_color(), dusty_agent.body)
                    pygame.draw.line(
                        surface, WHITE,
                        dusty_agent.body.center, dusty_agent.body.center + dusty_agent.direction * 50, 10)

            for bullet in self.bullets:
                pygame.draw.rect(surface, bullet.get_color(), bullet)

            for energy in self.energies:
                pygame.draw.rect(surface, energy.get_color(), energy)
            
            scaled_screen = pygame.transform.scale(
                surface, (self.map.grid_width, self.map.grid_height)
            )
            state = pygame.surfarray.array3d(scaled_screen)
            for agent in self.agents.values():
                x, y = agent.body.x // self.map.grid_cols, agent.body.y // self.map.grid_rows
                start_x, end_x, start_y, end_y = self.find_possible_state_area(x, y)
                self.obs[agent.id] = state[start_x:end_x, start_y:end_y]

        return pygame.transform.scale(
            surface, (display_width, display_height))

    def reset(self, seed=None, options=None):
        self.seed(seed)
        self.options = options
        """
            Reset the environment.
            This function is called at the beginning of each episode.            
        """
        if not seed:
            self.np_random, _ = seeding.np_random(seed)
        self.step_count = 0
        self.explosions.clear()
        self.energies.clear()
        self.bullets.clear()
        self.logs.clear()
        self.blue_scores.clear()
        self.yellow_scores.clear()
        self.map.reset(self.np_random)
        self.in_grid_energy_objects: dict[int, List[Energy]] = {
            i: []
            for i, _ in enumerate(self.map.large_grids)
        }

        if self.agents:
            blue_agents = [
                agent for agent in self.agents.values()
                if agent.team == Team.BLUE]
            yellow_agents = [
                agent for agent in self.agents.values()
                if agent.team == Team.YELLOW]

            blue_points = self.map.get_respwan_points(
                Team.BLUE, len(blue_agents))
            yellow_points = self.map.get_respwan_points(
                Team.YELLOW, len(yellow_agents))

            for point, agent in zip(blue_points, blue_agents):
                agent.reset(point, self.np_random)

            for point, agent in zip(yellow_points, yellow_agents):
                agent.reset(point, self.np_random)

        self.obs = {
            agent_id: np.zeros(self.observation_shape, dtype=np.uint8)
            for agent_id in self.agents
        }
        initial_infos = self.get_initial_infos()
        return self.get_observations(), initial_infos

    def seed(self, seed=None):
        self.np_random, seed = seeding.np_random(seed)
        return [seed]

    def objects_clear(self):
        while self.removing_agents:
            agent = self.removing_agents.pop()
            agent and self.remove_agent(agent)

        # 나중에 다 이렇게 하면 좋을듯?
        while self.removing_energies:
            energy = self.removing_energies.pop()
            energy and self.remove_energy(energy)

        while self.removing_bullets:
            bullet = self.removing_bullets.pop()
            bullet and self.remove_bullet(bullet)

    def step(self, actions: dict[str, list[DustyActiveAction | DustyControlAction]]):
        # 일단 기본 obs를 돌려준다.
        # 나중 최종 목표는 state에 obs를 만드는데 필요한 정보를 넣어서 돌려주는 것이다.
        #
        # action의 정의
        # 모든 agent는 action이 없으면 Forward Action을 한다.
        for agent_id, action in actions.items():
            match action[0]:
                case 0: actions[agent_id] = [None]
                case 1: actions[agent_id] = [25]
                case 2: actions[agent_id] = [26]
                case 3: actions[agent_id] = [27]
                case 4: actions[agent_id] = [28]
                case 5: actions[agent_id] = [50]
                case 6: actions[agent_id] = [51]
                case 7: actions[agent_id] = [52]
                case 8: actions[agent_id] = [53]
                case _: actions[agent_id] = action
        self.actions = actions
        self.logs.next_step()
        for agent in self.agents.values():
            if not agent.alive:
                self.reset_agent(agent)
                continue
            if agent.id in actions:
                agent.act(actions[agent.id])
            else:
                agent.act([])

        for bullet in self.bullets:
            bullet.act()

        # TODO package skill launcher
        for agent in self.agents.values():
            if agent.load_bullet:
                self.fire_bullet(agent)
                agent.load_bullet = False

        self.collision_processing(self.check_collisions())

        self.respwan_energy()
        self.objects_clear()
        self.render()

        obs = self.get_observations()
        rewards = self.get_rewards()
        infos = self.get_infos()
        truncateds = self.get_truncateds()
        terminateds = self.get_terminateds()
        self.step_count += 1
        return obs, rewards, terminateds, truncateds, infos


class DustySingleEnv(gym.Env):

    def __init__(self, **env_config) -> None:
        self.env = DustyEnv(**env_config)
        assert len(self.env.agents) == 1
        self.agent_id = list(self.env.agents.keys())[0]
        self.observation_space = self.env.observation_space
        self.action_space = self.env.action_space

    def step(self, action: list[DustyActiveAction | DustyControlAction]):
        obs, rewards, terminateds, truncateds, infos = self.env.step(
            {self.agent_id: action})
        return obs[self.agent_id], rewards[self.agent_id], terminateds[self.agent_id], truncateds[self.agent_id], infos[self.agent_id]

    def reset_agent(self):
        self.env.reset_agent(self.env.agents[self.agent_id])

    def reset(self, seed=None, options=None):
        obs, initial_info = self.env.reset(seed, options)
        return obs[self.agent_id], initial_info[self.agent_id]

    def render(self, **kwargs):
        return self.env.render(**kwargs)
