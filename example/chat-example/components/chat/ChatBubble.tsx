import { MessageData, LikeOrDislike } from "@/@types/chat";
import { useChat } from "@/hooks/useChat";
import { authAtom } from "@/store/authAtom";
import { useAtomValue } from "jotai";
import { useId, useState } from "react";
import ChatLinkPreview from "./ChatLinkPreview";

interface ChatBubbleProps {
  message: MessageData;
}

const ChatBubble = ({ message }: ChatBubbleProps) => {
  const { sendNotice, sendLike } = useChat();
  const likeRadioName = useId();
  const [isReported, setIsReported] = useState(false);
  const { id } = useAtomValue(authAtom);

  const {
    message: messageText,
    message_id,
    time,
    user: { user_id: userId, user_name: username },
    like,
  } = message;

  const onClickNotice = () => {
    sendNotice(messageText, userId.toString());
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

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`indicator dropdown dropdown-hover dropdown-bottom chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe ? "chat-bubble-primary" : "chat-bubble-secondary"
        }`}
      >
        {like > 0 ? (
          <span
            className={`indicator-item badge badge-accent ${
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
      <time className="chat-footer opacity-50">
        {new Date(time).toLocaleString()}
      </time>
      <ChatLinkPreview messageText={messageText} />
    </div>
  );
};

export default ChatBubble;
