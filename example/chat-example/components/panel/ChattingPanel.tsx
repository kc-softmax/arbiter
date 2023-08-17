import { ChatInfo } from "@/@types/chat";
import { useChat } from "@/app/hooks/useChat";
import ChatInputForm from "../chat/ChatInputForm";
import ChatRoom from "../chat/ChatRoom";

const tempToken =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2OTIyNTYwMzQsInN1YiI6IjEifQ.OQ7ojTi3I_qF7tT9ZKM5SxzEO_nQPBJ6UplTHuhympI";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { name } = chatInfo;
  const { roomId, messages, users, sendMessage, chatPanelRef, eventMessage } =
    useChat(tempToken);

  const sendChat = (message: string) => {
    console.log(name, message);
    sendMessage(message);
  };

  return (
    <section>
      <div className="p-4 h-screen">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-lg border-2 max-w-4xl mx-auto p-4">
          <div ref={chatPanelRef} className="flex-1 w-full overflow-scroll">
            <ChatRoom
              chatInfo={chatInfo}
              bannerInfo={{
                roomId,
                users,
              }}
              chatData={messages}
              eventMessage={eventMessage}
            />
          </div>
          <div className="w-full">
            <ChatInputForm sendChat={sendChat} />
          </div>
        </div>
      </div>
    </section>
  );
};

export default ChattingPanel;
