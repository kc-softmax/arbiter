import React from "react";

export interface ChatBannerProps {
  roomId: string;
  users: string[];
}

const ChatBanner = ({ roomId, users }: ChatBannerProps) => {
  return (
    <div className="text-center">
      <p className="font-semibold">{roomId}</p>
      <p>
        {users.map((user) => (
          <span key={user} className="badge">
            {user}
          </span>
        ))}
      </p>
    </div>
  );
};

export default ChatBanner;
