import { useChat } from "@/hooks/useChat";
import { sortTargetItemFirst } from "@/utils/sort-utils";
import { useState } from "react";

const ChatLobby = () => {
  const {
    createRoom,
    changeRoom,
    refreshLobby,
    data: { lobbyRoomList, roomId: currentRoomId },
  } = useChat();

  const [searchInput, setSearchInput] = useState("");

  const onClickCreateRoom = () => {
    const nextRoomId = prompt("Type Room ID");

    if (!nextRoomId) return;

    createRoom(nextRoomId);
    changeRoom(nextRoomId);
  };

  const onClickRoom = (roomId: string) => {
    changeRoom(roomId);
  };

  return (
    <section className="h-full">
      <div className="p-4 overflow-scroll h-full space-y-4 relative">
        <div className="space-y-2">
          <button
            className="btn btn-primary btn-lg btn-block"
            onClick={onClickCreateRoom}
          >
            Create Room
          </button>
          <button className="btn btn-secondary btn-lg btn-block">
            Match Start
          </button>
        </div>
        <div className="divider" />
        <div>
          <input
            type="text"
            placeholder="Search..."
            className="input input-bordered input-lg w-full"
            onChange={(e) => setSearchInput(e.target.value)}
            value={searchInput}
          />
        </div>
        <ul className="flex flex-col gap-2">
          {lobbyRoomList
            .filter(
              ({ room_id: roomId }) =>
                roomId.toLowerCase().indexOf(searchInput.toLowerCase()) > -1
            )
            .sort((a, b) =>
              sortTargetItemFirst(a.room_id, b.room_id, currentRoomId)
            )
            .map(
              ({
                room_id: roomId,
                current_users: currentUsers,
                max_users: maxUsers,
              }) => (
                <li key={roomId} onClick={() => onClickRoom(roomId)}>
                  <div
                    className={`card border ${
                      currentRoomId === roomId
                        ? "bg-primary text-primary-content"
                        : "bg-base-100 hover:brightness-90 cursor-pointer"
                    }`}
                  >
                    <div className="card-body p-6">
                      <h2 className="card-title">
                        {roomId} {currentRoomId === roomId ? "(current)" : ""}
                      </h2>
                      <p>
                        users: {currentUsers} / {maxUsers}
                      </p>
                    </div>
                  </div>
                </li>
              )
            )}
        </ul>
        <div className="absolute bottom-4 right-4">
          <button className="btn btn-circle btn-lg" onClick={refreshLobby}>
            ♻️
          </button>
        </div>
      </div>
    </section>
  );
};

export default ChatLobby;
