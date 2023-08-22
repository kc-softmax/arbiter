import { ChatMessage, MessageInfo, UserInfo } from "@/@types/chat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";

const ChatBubble = ({ user, message, time }: ChatMessage) => {
  const { id } = useAtomValue(authAtom);
  const { id: userId, name: username } = user;
  const { id: messageId, message: messageText } = message;

  const onClickReport = () => {
    alert(`Report ${username}'s ${messageId} at ${time}`);
  };

  const isMe = id === userId;

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`dropdown dropdown-hover dropdown-right chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe ? "chat-bubble-primary" : "chat-bubble-secondary"
        }`}
      >
        <p className="hover:brightness-90 transition-all">{messageText}</p>
        <div
          tabIndex={0}
          className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box"
        >
          <button className="btn btn-error btn-outline" onClick={onClickReport}>
            Report
          </button>
        </div>
      </div>
      <time className="chat-footer opacity-50">{time}</time>
    </div>
  );
};

export default ChatBubble;
