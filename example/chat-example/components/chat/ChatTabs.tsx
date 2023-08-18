import { ChatTabList, ChatTabType } from "@/const/actions";
import { Dispatch, useState } from "react";

interface ChatTabsProps {
  onChange: Dispatch<ChatTabType>;
}

const ChatTabs = ({ onChange }: ChatTabsProps) => {
  const [activeTab, setActiveTab] = useState<ChatTabType>("all");

  const onClickTab = (tab: ChatTabType) => {
    setActiveTab(tab);
    onChange(tab);
  };

  return (
    <div className="tabs tabs-boxed">
      {Object.entries(ChatTabList).map(([key, value]) => (
        <a
          key={key}
          className={`tab ${activeTab === value ? "tab-active" : ""}`}
          onClick={() => onClickTab(value)}
        >
          {value.toUpperCase()}
        </a>
      ))}
    </div>
  );
};

export default ChatTabs;
