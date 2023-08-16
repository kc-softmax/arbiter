interface ChatBubbleProps {
  username: string;
  message: string;
  time: string;
  isMe?: boolean;
}

const ChatBubble = ({
  username,
  message,
  time,
  isMe = false,
}: ChatBubbleProps) => {
  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <p
        className={`chat-bubble flex justify-center items-end ${
          isMe ? "chat-bubble-primary" : "chat-bubble-secondary"
        }`}
      >
        {message}
      </p>
      <time className="chat-footer opacity-50">{time}</time>
    </div>
  );
};

export default ChatBubble;
