import { useState } from "react";

interface UseCommandInputParams {
  [command: string]: () => void;
}

export const useCommandInput = (commands: UseCommandInputParams) => {
  const [messageInput, setMessageInput] = useState("");
  const [command, setCommand] = useState<string | null>(null);

  const resetMessageInput = () => {
    setMessageInput("");
  };

  const resetCommand = () => {
    setCommand(null);
  };

  const onChangeMessageText = (e: React.ChangeEvent<HTMLTextAreaElement>) => {
    setMessageInput(e.target.value);

    Object.keys(commands).forEach((command) => {
      const commandRegex = new RegExp(`^${command}\\s+`);
      const commandMatch = e.target.value.match(commandRegex);

      if (commandMatch) {
        commands[command]();
        setCommand(command);
        setMessageInput("");

        return;
      }
    });
  };

  return {
    command,
    controls: {
      message: {
        value: messageInput,
        onChange: onChangeMessageText,
      },
    },
    reset: resetMessageInput,
    resetCommand,
  };
};
