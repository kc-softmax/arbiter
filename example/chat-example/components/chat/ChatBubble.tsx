import { MessageData } from "@/@types/chat";
import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useState } from "react";
import ChatLinkPreview from "./ChatLinkPreview";

interface ChatBubbleProps {
  message: MessageData;
}

const ChatBubble = ({ message }: ChatBubbleProps) => {
  const {
    sendNotice,
    sendLike,
    changeRoom,
    data: { roomId: connectedRoomId },
  } = useChat();
  const [isReported, setIsReported] = useState(false);
  const { id } = useAtomValue(authAtom);

  const {
    message: messageText,
    message_id,
    time,
    user: { user_id: userId, user_name: username },
    like,
    room_id: messageRoomId,
  } = message;

  const onClickNotice = () => {
    sendNotice(messageText);
  };

  const onClickReport = () => {
    alert(`Reported: ${userId}-${username}'s ${messageText}`);
    setIsReported(true);
  };

  const onChangeLike = (e: React.ChangeEvent<HTMLInputElement>) => {
    const type = e.target.checked ? "like" : "dislike";

    sendLike(message_id, type);
  };

  const isMe = id === userId.toString();
  const isOtherRoom = connectedRoomId !== messageRoomId;

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <div className="chat-header flex flex-row gap-1 items-center">
        <p>{username}</p>
        <button
          className="badge badge-outline badge-primary badge-sm cursor-pointer hover:bg-primary hover:text-primary-content hover:border-primary"
          onClick={() => changeRoom(messageRoomId)}
        >
          {messageRoomId}
        </button>
      </div>
      <div
        tabIndex={0}
        className={`indicator dropdown dropdown-hover dropdown-bottom chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] 
        ${isMe ? "chat-bubble-primary" : "chat-bubble-secondary"} 
        ${isOtherRoom ? "bg-opacity-60 text-gray-700" : ""}
        `}
      >
        {like > 0 ? (
          <span
            className={`indicator-item indicator-bottom badge badge-accent ${
              isMe ? "indicator-start" : "indicator-end"
            }`}
          >
            👍 {like}
          </span>
        ) : null}

        <p>{isReported ? "Reported 🚨" : messageText}</p>

        <div
          tabIndex={0}
          className={`dropdown-content z-20 p-2 shadow bg-base-100 rounded-box flex flex-col gap-2 w-32 ${
            isMe ? "right-0" : "left-0"
          }`}
        >
          <input
            type="checkbox"
            className="btn btn-outline btn-sm btn-success radio rounded-lg"
            aria-label="👍"
            onChange={onChangeLike}
          />
          <button className="btn btn-info btn-outline" onClick={onClickNotice}>
            Notice
          </button>
          <button className="btn btn-error btn-outline" onClick={onClickReport}>
            Report
          </button>
        </div>
      </div>
      <time className="chat-footer opacity-50 text-xs">
        {new Date(time).toLocaleTimeString()}
      </time>
      <ChatLinkPreview messageText={messageText} />
    </div>
  );
};

export default ChatBubble;
