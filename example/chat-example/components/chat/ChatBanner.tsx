import React from "react";

export interface ChatBannerProps {
  roomId: string;
  users: string[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  return (
    <div className="text-center sticky top-0">
      <p className="font-semibold">RoomID: {roomId}</p>
      <p>
        {users.map((user, index) => (
          <span key={user + index} className="badge">
            {user}
          </span>
        ))}
      </p>
    </div>
  );
};

export default ChatBanner;
