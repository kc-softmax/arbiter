import { ChatSocketMessageBase } from "@/@types/chat";
import { ChatActions } from "@/const/actions";
import { authAtom } from "@/store/authAtom";
import {
  chatAddMessageAtom,
  chatAtom,
  chatRoomJoinAtom,
  chatSetErrorAtom,
  chatSetEventMessageAtom,
  chatSetInviteUserAtom,
  chatSetLobbyAtom,
  chatSetNoticeAtom,
  chatUpdateLikesAtom,
  chatUserJoinAtom,
  chatUsesrLeaveAtom,
} from "@/store/chatAtom";
import { useAtom, useAtomValue, useSetAtom } from "jotai";
import { PropsWithChildren, useCallback, useEffect } from "react";

const HostAddress = process.env.NEXT_PUBLIC_HOST;

const ChatProvider = ({ children }: PropsWithChildren) => {
  const [{ ws }, setChatState] = useAtom(chatAtom);
  const { token } = useAtomValue(authAtom);

  const setEventMessage = useSetAtom(chatSetEventMessageAtom);
  const setRoomData = useSetAtom(chatRoomJoinAtom);
  const addMessage = useSetAtom(chatAddMessageAtom);
  const addUser = useSetAtom(chatUserJoinAtom);
  const removeUser = useSetAtom(chatUsesrLeaveAtom);
  const setNotice = useSetAtom(chatSetNoticeAtom);
  const setError = useSetAtom(chatSetErrorAtom);
  const setLobbyRoomList = useSetAtom(chatSetLobbyAtom);
  const setInviteUser = useSetAtom(chatSetInviteUserAtom);
  const updateLike = useSetAtom(chatUpdateLikesAtom);

  const join = useCallback(
    (ws: WebSocket) => {
      ws.onopen = () => {
        console.log("Chat connected");
      };

      ws.onclose = (event) => {
        console.log("Chat disconnected", event);
        alert(event.reason || "Chat disconnected");
      };

      ws.onmessage = (event) => {
        const chatSocketMessage: ChatSocketMessageBase = JSON.parse(event.data);
        const { action, data } = chatSocketMessage;
        console.log(
          "🚀 ~ file: useChat.tsx:46 ~ join ~ chatSocketMessage:",
          chatSocketMessage
        );

        setEventMessage(chatSocketMessage);

        switch (action) {
          case ChatActions.ROOM_JOIN: {
            setRoomData(data);
            break;
          }
          case ChatActions.USER_JOIN: {
            addUser(data.user);
            break;
          }
          case ChatActions.USER_LEAVE: {
            removeUser(data.user);
            break;
          }
          case ChatActions.MESSAGE:
          case ChatActions.CONTROL: {
            addMessage(data);
            break;
          }
          case ChatActions.NOTICE: {
            setNotice(data.message);
            break;
          }
          case ChatActions.ERROR: {
            setError(data);
            break;
          }
          case ChatActions.ROOM_CREATE: {
            alert(data.message);
            break;
          }
          case ChatActions.LOBBY_REFRESH: {
            setLobbyRoomList(data);
            break;
          }
          case ChatActions.USER_INVITE: {
            setInviteUser(data);
            break;
          }
          case ChatActions.MESSAGE_LIKE: {
            updateLike(data);
            break;
          }
          default: {
            setError({
              code: 0,
              reason: `Unhandled action: ${action}`,
            });

            break;
          }
        }
      };
    },
    [
      setEventMessage,
      setRoomData,
      addMessage,
      addUser,
      removeUser,
      setNotice,
      setError,
      setLobbyRoomList,
      setInviteUser,
      updateLike,
    ]
  );

  useEffect(() => {
    if (!HostAddress) {
      throw new Error("Host Address is not defined");
    }

    if (!ws) {
      const websocketAddress = HostAddress.replace(/^https?/, "ws");
      const ws = new WebSocket(`${websocketAddress}/chat/ws?token=${token}`);

      setChatState((prev) => ({
        ...prev,
        ws,
      }));

      join(ws);
    }

    return () => {
      ws?.close();
    };
  }, [token, ws, setChatState, join]);

  return <>{children}</>;
};

export default ChatProvider;
