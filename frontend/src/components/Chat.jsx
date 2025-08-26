import React, { useState, useEffect, useRef } from 'react';
import { chatAPI } from '../services/api';
import { useAuth } from '../contexts/AuthContext';

const Chat = () => {
  const [chats, setChats] = useState([]);
  const [activeChat, setActiveChat] = useState(null);
  const [messages, setMessages] = useState([]);
  const [newMessage, setNewMessage] = useState('');
  const [newChatTitle, setNewChatTitle] = useState('');
  const [loading, setLoading] = useState(false);
  const [showNewChatForm, setShowNewChatForm] = useState(false);
  const messagesEndRef = useRef(null);

  const { user, logout } = useAuth();

  useEffect(() => {
    loadChats();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const loadChats = async () => {
    try {
      const chatList = await chatAPI.getChats();
      setChats(chatList);
    } catch (error) {
      console.error('Failed to load chats:', error);
    }
  };

  const selectChat = async (chat) => {
    setActiveChat(chat);
    try {
      const chatData = await chatAPI.getChat(chat.id);
      setMessages(chatData.messages || []);
    } catch (error) {
      console.error('Failed to load chat messages:', error);
    }
  };

  const createNewChat = async (e) => {
    e.preventDefault();
    if (!newChatTitle.trim()) return;

    console.log('🔄 Opretter ny chat med titel:', newChatTitle);
    
    try {
      const newChat = await chatAPI.createChat(newChatTitle);
      console.log('✅ Chat oprettet succesfuldt:', newChat);
      setChats([newChat, ...chats]);
      setNewChatTitle('');
      setShowNewChatForm(false);
      selectChat(newChat);
    } catch (error) {
      console.error('❌ Fejl ved oprettelse af chat:', error);
      console.error('Error details:', error.response?.data);
      alert(`Fejl ved oprettelse af chat: ${error.response?.data?.detail || error.message}`);
    }
  };

  const sendMessage = async (e) => {
    e.preventDefault();
    if (!newMessage.trim() || !activeChat) return;

    console.log('📤 Sender besked:', newMessage, 'til chat:', activeChat.id);

    const userMessage = {
      role: 'user',
      content: newMessage,
      created_at: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setNewMessage('');
    setLoading(true);

    try {
      const response = await chatAPI.sendMessage(activeChat.id, newMessage);
      console.log('✅ Besked sendt, svar modtaget:', response);
      setMessages(prev => [...prev, response.message]);
    } catch (error) {
      console.error('❌ Fejl ved sending af besked:', error);
      console.error('Error details:', error.response?.data);
      alert(`Fejl ved sending af besked: ${error.response?.data?.detail || error.message}`);
      setMessages(prev => prev.slice(0, -1)); // Remove user message on error
    } finally {
      setLoading(false);
    }
  };

  const deleteChat = async (chatId) => {
    if (!confirm('Er du sikker på, at du vil slette denne chat?')) return;

    try {
      await chatAPI.deleteChat(chatId);
      setChats(chats.filter(chat => chat.id !== chatId));
      if (activeChat?.id === chatId) {
        setActiveChat(null);
        setMessages([]);
      }
    } catch (error) {
      console.error('Failed to delete chat:', error);
    }
  };

  const formatTime = (timestamp) => {
    return new Date(timestamp).toLocaleTimeString('da-DK', {
      hour: '2-digit',
      minute: '2-digit',
    });
  };

  return (
    <div className="chat-container">
      <header className="chat-header">
        <h1>SRIC</h1>
        <div className="user-info">
          <span>Velkommen, {user?.username}</span>
          <button onClick={logout} className="logout-btn">Log ud</button>
        </div>
      </header>

      <div className="chat-layout">
        {/* Sidebar with chat list */}
        <div className="chat-sidebar">
          <div className="sidebar-header">
            <h3>Mine Chats</h3>
            <button 
              onClick={() => setShowNewChatForm(true)}
              className="new-chat-btn"
            >
              + Ny Chat
            </button>
          </div>

          {showNewChatForm && (
            <form onSubmit={createNewChat} className="new-chat-form">
              <input
                type="text"
                value={newChatTitle}
                onChange={(e) => setNewChatTitle(e.target.value)}
                placeholder="Chat titel..."
                autoFocus
              />
              <div className="form-buttons">
                <button type="submit">Opret</button>
                <button 
                  type="button" 
                  onClick={() => setShowNewChatForm(false)}
                >
                  Annuller
                </button>
              </div>
            </form>
          )}

          <div className="chat-list">
            {chats.map((chat) => (
              <div
                key={chat.id}
                className={`chat-item ${activeChat?.id === chat.id ? 'active' : ''}`}
                onClick={() => selectChat(chat)}
              >
                <div className="chat-title">{chat.title}</div>
                <div className="chat-meta">
                  {new Date(chat.created_at).toLocaleDateString('da-DK')}
                </div>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    deleteChat(chat.id);
                  }}
                  className="delete-chat-btn"
                >
                  🗑️
                </button>
              </div>
            ))}
          </div>
        </div>

        {/* Main chat area */}
        <div className="chat-main">
          {activeChat ? (
            <>
              <div className="chat-messages">
                {messages.map((message, index) => (
                  <div
                    key={index}
                    className={`message ${message.role === 'user' ? 'user-message' : 'assistant-message'}`}
                  >
                    <div className="message-content">
                      <div className="message-text">{message.content}</div>
                      <div className="message-time">
                        {formatTime(message.created_at)}
                      </div>
                    </div>
                    {message.sources && (
                      <div className="message-sources">
                        <strong>Kilder:</strong>{' '}
                        {JSON.parse(message.sources).map((src, i) => {
                          // Hvis src ligner et filnavn, vis det, ellers vis som før
                          if (typeof src === 'string' && src.match(/\.(pdf|docx|eml|xlsx)$/i)) {
                            return <span key={i}>{src}{i < JSON.parse(message.sources).length - 1 ? ', ' : ''}</span>;
                          } else {
                            return <span key={i}>{src}{i < JSON.parse(message.sources).length - 1 ? ', ' : ''}</span>;
                          }
                        })}
                      </div>
                    )}
                  </div>
                ))}
                {loading && (
                  <div className="message assistant-message">
                    <div className="message-content">
                      <div className="typing-indicator">
                        <span></span>
                        <span></span>
                        <span></span>
                      </div>
                    </div>
                  </div>
                )}
                <div ref={messagesEndRef} />
              </div>

              <form onSubmit={sendMessage} className="message-form">
                <input
                  type="text"
                  value={newMessage}
                  onChange={(e) => setNewMessage(e.target.value)}
                  placeholder="Skriv dit spørgsmål her..."
                  disabled={loading}
                />
                <button type="submit" disabled={loading || !newMessage.trim()}>
                  Send
                </button>
              </form>
            </>
          ) : (
            <div className="no-chat-selected">
              <h3>Vælg en chat eller opret en ny</h3>
              <p>Systemet kan besvare spørgsmål baseret på tidligere samtaler.</p>
              <div className="example-questions">
                <h4>Eksempel på kontekstuelle spørgsmål:</h4>
                <ul>
                  <li><strong>Spørgsmål 1:</strong> "Hvem er kunden på police nr 1001?"</li>
                  <li><strong>Spørgsmål 2:</strong> "Hvad dækker den?" (systemet forstår "den" = police 1001)</li>
                </ul>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default Chat;
