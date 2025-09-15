// Generic chat client used by room, private and group templates.
const socket = io();

// Utility to append message bubble
function appendMessage(box, text, kind = 'received', msgId=null){
  const el = document.createElement('div');
  el.className = 'bubble ' + kind;
  if(msgId) el.dataset.msgId = msgId;
  el.innerHTML = `<div class=\"meta\">${text.split(':')[0]} <span class=\"ts\"></span></div><div class=\"text\">${text.split(':').slice(1).join(':')}</div>`;
  box.appendChild(el);
  box.scrollTop = box.scrollHeight;
  return el;
}

// ROOM PAGE behavior
if(typeof ROOM !== 'undefined'){
  const chatBox = document.getElementById('chat-box');
  const sendBtn = document.getElementById('sendBtn');
  const msgInput = document.getElementById('msg');

  socket.emit('join',{room: ROOM, username: USERNAME});

  socket.on('message', (data) => {
    // server sends {msg: 'username: message'}
    appendMessage(chatBox, data.msg, data.msg.startsWith(USERNAME + ':') ? 'sent' : 'received');
  });

  sendBtn?.addEventListener('click', ()=>{
    const m = msgInput.value.trim();
    if(!m) return;
    socket.emit('room_message',{room: ROOM, username: USERNAME, msg: m});
    msgInput.value = '';
  });

  msgInput?.addEventListener('keypress', (e)=>{ if(e.key==='Enter') sendBtn.click(); });
}

// PRIVATE 1-to-1 page behavior
if(typeof PRIVATE_PEER_ID !== 'undefined'){
  const chatBox = document.getElementById('chat-box');
  const sendBtn = document.getElementById('sendBtn');
  const msgInput = document.getElementById('msg');

  // join own private room (where peer sends to "private_<id>")
  socket.emit('join_private',{peer_id: PRIVATE_PEER_ID});

  socket.on('message', (data) => {
    appendMessage(chatBox, data.msg, data.msg.startsWith(USERNAME + ':') ? 'sent' : 'received');
  });

  sendBtn?.addEventListener('click', ()=>{
    const m = msgInput.value.trim();
    if(!m) return;
    socket.emit('private_message',{username: USERNAME, peer: PRIVATE_PEER, msg: m});
    msgInput.value = '';
  });

  msgInput?.addEventListener('keypress', (e)=>{ if(e.key==='Enter') sendBtn.click(); });
}

// GROUP page behavior
if(typeof GROUP_ID !== 'undefined'){
  const chatBox = document.getElementById('chat-box');
  const sendBtn = document.getElementById('sendBtn');
  const msgInput = document.getElementById('msg');

  socket.emit('join_private_group',{group_id: GROUP_ID, username: USERNAME});

  socket.on('message', (data) => {
    appendMessage(chatBox, data.msg, data.msg.startsWith(USERNAME + ':') ? 'sent' : 'received');
  });

  sendBtn?.addEventListener('click', ()=>{
    const m = msgInput.value.trim();
    if(!m) return;
    socket.emit('private_group_message',{group_id: GROUP_ID, username: USERNAME, msg: m});
    msgInput.value = '';
  });

  msgInput?.addEventListener('keypress', (e)=>{ if(e.key==='Enter') sendBtn.click(); });
}

// Typing indicators (generic)
let typingTimeout;
const sendTyping = (roomOrTarget) => {
  socket.emit('typing',{username: USERNAME, room: roomOrTarget});
  clearTimeout(typingTimeout);
  typingTimeout = setTimeout(()=> socket.emit('stop_typing',{username: USERNAME, room: roomOrTarget}), 1200);
};

// show typing
socket.on('typing', (data)=>{
  // optional: show small toast or typing indicator in page
  const el = document.querySelector('.typing');
  if(el) el.textContent = `${data.username} is typing...`;
});
socket.on('stop_typing', ()=>{
  const el = document.querySelector('.typing'); if(el) el.textContent = '';
});

// mark message read by click
document.addEventListener('click', (e)=>{
  const b = e.target.closest('.bubble');
  if(b && b.dataset.msgId){
    socket.emit('message_read', { message_id: b.dataset.msgId });
  }
});
