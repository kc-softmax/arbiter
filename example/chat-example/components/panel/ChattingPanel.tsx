import { ChatInfo } from "@/@types/chat";
import { useChat } from "@/app/hooks/useChat";
import ChatInputForm from "../chat/ChatInputForm";
import ChatRoom from "../chat/ChatRoom";

const tempToken =
  "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJleHAiOjE2OTE0NzQxMDksInN1YiI6ImhvbmdAa2MuY29tIiwibG9naW5fdHlwZSI6ImVtYWlsIn0.tjOMAnNUG_oKf9JP4q93wI7mmOkHMF-Dn8KQtZM0mQo";

interface ChattingPanelProps {
  chatInfo: ChatInfo;
}

const ChattingPanel = ({ chatInfo }: ChattingPanelProps) => {
  const { name } = chatInfo;
  const { roomId, messages, users, sendMessage, chatPanelRef, eventMessage } =
    useChat(name, tempToken);

  const sendChat = (message: string) => {
    console.log(name, message);
    sendMessage(message);
  };

  return (
    <section>
      <div className="p-4 h-screen">
        <div className="flex flex-col gap-4 justify-center items-center h-full rounded-lg border-2 max-w-4xl mx-auto p-4">
          <div className="flex-1 w-full">
            <ChatRoom
              chatInfo={chatInfo}
              bannerInfo={{
                roomId,
                users,
              }}
              chatData={messages}
              chatListRef={chatPanelRef}
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
