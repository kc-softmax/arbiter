import React from "react";

interface StartChatPanelProps extends React.HTMLAttributes<HTMLButtonElement> {}

const StartChatPanel = ({ onClick, ...props }: StartChatPanelProps) => {
  return (
    <section>
      <div className="h-screen flex justify-center items-center">
        <button {...props} className="btn btn-primary btn-lg" onClick={onClick}>
          Start Chat
        </button>
      </div>
    </section>
  );
};

export default StartChatPanel;
