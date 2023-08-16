import React from "react";

interface ChatBubbleProps {
  username: string;
  message: string;
  time: string;
}

export const MyChatBubble = ({ username, message, time }: ChatBubbleProps) => {
  return (
    <div className="chat chat-end">
      <p className="chat-header">{username}</p>
      <p className="chat-bubble chat-bubble-primary flex justify-center items-end">
        {message}
      </p>
      <time className="chat-footer opacity-50">{time}</time>
    </div>
  );
};

export const OtherChatBubble = ({
  username,
  message,
  time,
}: ChatBubbleProps) => {
  return (
    <div className="chat chat-start">
      <p className="chat-header">{username}</p>
      <p className="chat-bubble chat-bubble-secondary flex justify-center items-end">
        {message}
      </p>
      <time className="chat-footer opacity-50">{time}</time>
    </div>
  );
};
