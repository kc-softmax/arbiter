import { useState } from "react";

const dummyData = [
  {
    id: "1",
    roomId: "Room1",
    users: 1,
  },
  {
    id: "2",
    roomId: "Room2",
    users: 2,
  },
  {
    id: "3",
    roomId: "Room3",
    users: 3,
  },
];

interface ChatLobbyProps {
  changeRoom: (roomId: string) => void;
}

const ChatLobby = ({ changeRoom }: ChatLobbyProps) => {
  const [searchInput, setSearchInput] = useState("");

  const createRoom = () => {
    const nextRoomId = prompt("Type Room ID");

    if (!nextRoomId) return;

    changeRoom(nextRoomId);
  };

  const onClickRoom = (roomId: string) => {
    changeRoom(roomId);
  };

  return (
    <section className="h-full">
      <div className="p-4 overflow-scroll h-full space-y-4">
        <div className="space-y-2">
          <button
            className="btn btn-primary btn-lg btn-block"
            onClick={createRoom}
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
          {dummyData
            .filter(
              ({ roomId }) =>
                roomId.toLowerCase().indexOf(searchInput.toLowerCase()) > -1
            )
            .map(({ id, roomId, users }) => (
              <li key={id} onClick={() => onClickRoom(roomId)}>
                <div className="card bg-base-100 hover:brightness-90 cursor-pointer border">
                  <div className="card-body p-6">
                    <h2 className="card-title">{roomId}</h2>
                    <p>users: {users}</p>
                  </div>
                </div>
              </li>
            ))}
        </ul>
      </div>
    </section>
  );
};

export default ChatLobby;
