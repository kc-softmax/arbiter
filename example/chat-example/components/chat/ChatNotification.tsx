import React from "react";

interface ChatNotificationProps {
  username: string;
  enter: boolean;
}

const ChatNotification = ({ enter, username }: ChatNotificationProps) => {
  return (
    <div className="text-center">
      {enter ? (
        <p>
          <span className="font-bold">{username}</span>님이 입장하였습니다.
        </p>
      ) : (
        <p>
          <span className="font-bold">{username}</span>님이 퇴장하였습니다.
        </p>
      )}
    </div>
  );
};

export default ChatNotification;
