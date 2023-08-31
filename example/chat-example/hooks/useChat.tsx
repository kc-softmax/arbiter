"use client";

import { ChatSendMessage, LikeOrDislike } from "@/@types/chat";
import { ChatActionType, ChatActions } from "@/const/actions";
import { chatAtom } from "@/store/chatAtom";
import { useAtomValue } from "jotai";

export const useChat = () => {
  const {
    error,
    eventMessage,
    messages,
    notice,
    roomId,
    users,
    ws,
    lobbyRoomList,
    inviteMessage,
  } = useAtomValue(chatAtom);

  const sendSocketBase = <T extends object>(
    action: ChatActionType,
    data: T
  ) => {
    const chatData: {
      action: ChatActionType;
      data: T;
    } = {
      action,
      data,
    };

    ws?.send(JSON.stringify(chatData));
  };

  const sendMessage = ({ message, user_id }: ChatSendMessage["data"]) => {
    sendSocketBase(ChatActions.MESSAGE, {
      message,
      user_id,
    });
  };

  const createRoom = (nextRoomId: string, maxUsers: number = 8) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CREATE, {
      room_id: nextRoomId,
      max_users: maxUsers,
    });
  };

  const changeRoom = (nextRoomId: string) => {
    if (roomId === nextRoomId) return;

    sendSocketBase(ChatActions.ROOM_CHANGE, {
      room_id: nextRoomId,
    });
  };

  const sendNotice = (message: string, userId: string) => {
    sendSocketBase(ChatActions.NOTICE, {
      message,
      user_id: userId,
    });
  };

  const sendWhisper = ({
    message,
    userId,
    whisperTarget,
  }: {
    message: string;
    userId: string;
    whisperTarget: string;
  }) => {
    console.log(
      "userId, message, whisperTarget :>> ",
      userId,
      message,
      whisperTarget
    );
    // sendSocketBase(ChatActions.WHISPER, {
    //   message,
    //   user_id: userId,
    //   whisper_target: whisperTarget,
    // });
  };

  const refreshLobby = () => {
    sendSocketBase(ChatActions.LOBBY_REFRESH, {});
  };

  const inviteUser = ({
    userFrom,
    userTo,
  }: {
    userFrom: string;
    userTo: string;
  }) => {
    sendSocketBase(ChatActions.USER_INVITE, {
      room_id: roomId,
      user_id_from: parseInt(userFrom, 10),
      user_name_to: userTo,
    });
  };

  const sendLike = (messageId: number, type: LikeOrDislike) => {
    sendSocketBase(ChatActions.MESSAGE_LIKE, {
      message_id: messageId,
      type,
    });
  };

  return {
    data: {
      roomId,
      notice,
      messages,
      users,
      lobbyRoomList,
    },
    inviteMessage,
    error,
    eventMessage,
    sendMessage,
    createRoom,
    changeRoom,
    sendNotice,
    sendWhisper,
    refreshLobby,
    inviteUser,
    sendLike,
  };
};
