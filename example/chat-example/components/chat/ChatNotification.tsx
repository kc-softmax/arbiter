import React from "react";

interface ChatNotificationProps {
  username: string;
  enter: boolean;
}

const ChatNotification = ({ enter, username }: ChatNotificationProps) => {
  return (
    <div className="text-center">
      <p>
        <span className="font-bold">{username}</span>님이 {enter ? "입" : "퇴"}
        장하였습니다.
      </p>
    </div>
  );
};

export default ChatNotification;
