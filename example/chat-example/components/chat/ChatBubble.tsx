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
    const type = e.target.value as LikeOrDislike;
    sendLike(message_id, type);
  };

  const isMe = id === userId.toString();

  return (
    <div className={`chat ${isMe ? "chat-end" : "chat-start"}`}>
      <p className="chat-header">{username}</p>
      <div
        tabIndex={0}
        className={`indicator dropdown dropdown-hover dropdown-bottom dropdown-end chat-bubble flex justify-center items-end cursor-pointer max-w-[70%] ${
          isMe ? "chat-bubble-primary " : "chat-bubble-secondary "
        }`}
      >
        {like ? (
          <span
            className={`indicator-item badge badge-accent ${
              isMe ? "indicator-start" : "indicator-end"
            }`}
          >
            {like > 0 ? "👍" : "👎"} {like}
          </span>
        ) : null}

        <p>{isReported ? "Reported 🚨" : messageText}</p>

        <div
          tabIndex={0}
          className="dropdown-content z-20 p-2 shadow bg-base-100 rounded-box space-y-2 w-32"
        >
          <div className="join w-full">
            <input
              type="radio"
              name={likeRadioName}
              className="join-item flex-1 btn btn-outline btn-sm btn-success radio checked:bg-success rounded-lg"
              aria-label="👍"
              onChange={onChangeLike}
              value="like"
            />
            <input
              type="radio"
              name={likeRadioName}
              className="join-item flex-1 btn btn-outline btn-sm btn-error radio checked:bg-error rounded-lg"
              aria-label="👎"
              onChange={onChangeLike}
              value="dislike"
            />
          </div>
          <button
            className="btn btn-info btn-outline btn-block"
            onClick={onClickNotice}
          >
            Notice
          </button>
          <button
            className="btn btn-error btn-outline btn-block"
            onClick={onClickReport}
          >
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
