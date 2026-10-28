'use strict';
const $ = selector => document.querySelector(selector);
let history = [];
let accessCode = '';
let busy = false;
let listening = false;
let recognition;
let lastAnswer = '';
let speechTimer;
let ready = false;
let accessRequired = false;

function state(text, mode = '') {
  $('#voice-state').textContent = text;
  $('#orb').className = 'orb' + (mode ? ' ' + mode : '');
}
function error(message) { $('#error').textContent = message; }
function stopAudio() {
  clearTimeout(speechTimer);
  if ('speechSynthesis' in window) window.speechSynthesis.cancel();
}
function speak(text) {
  stopAudio();
  if (!('speechSynthesis' in window)) {
    error('Bu tarayıcı sesli yanıtı desteklemiyor. Yanıtı ekrandan okuyabilirsiniz.');
    return;
  }
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'tr-TR';
  const voice = window.speechSynthesis.getVoices().find(v => v.lang.startsWith('tr'));
  if (voice) utterance.voice = voice;
  utterance.rate = 1;
  let started = false;
  utterance.onstart = () => { started = true; clearTimeout(speechTimer); state('Asistan konuşuyor.'); };
  utterance.onend = () => state('Başka ne sormak istersiniz?');
  utterance.onerror = () => state('Ses başlayamadı. “Yanıtı sesli dinle” düğmesini deneyin.');
  window.speechSynthesis.speak(utterance);
  speechTimer = setTimeout(() => {
    if (!started) state('Yanıt hazır. Dinlemek için “Yanıtı sesli dinle” düğmesine dokunun.');
  }, 3000);
}
function bubble(role, text) {
  const node = document.createElement('article');
  node.className = 'bubble ' + role;
  const label = document.createElement('strong');
  label.textContent = role === 'user' ? 'SİZ' : 'ACENTE ASİSTANI';
  node.append(label, document.createTextNode(text));
  $('#conversation').append(node);
  node.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
  return node;
}
function controls() {
  $('#send').disabled = busy || listening || !ready;
  $('#mic').disabled = busy || !recognition;
  $('#mic').classList.toggle('recording', listening);
  $('#mic span').textContent = listening ? 'Konuşmayı bitir' : 'Konuşmaya başla';
  $('#clear').disabled = busy || listening;
  $('#message').disabled = busy || listening;
  $('#read-reply').disabled = busy || listening;
}
async function send() {
  const text = $('#message').value.trim();
  if (!text || busy || listening) return;
  if (!ready) { error('Yapay zekâ bağlantısı henüz etkin değil. Ayarlar bölümüne bakın.'); return; }
  if (accessRequired && !accessCode) { $('#settings').showModal(); $('#access-code').focus(); return; }
  if (text.length > 4000) { error('Lütfen mesajı 4000 karakterden kısa tutun.'); return; }
  stopAudio();
  error('');
  busy = true;
  controls();
  state('Sorunuzu düşünüyorum…', 'thinking');
  const userBubble = bubble('user', text);
  const messages = [...history.slice(-10), { role: 'user', text }];
  while (messages.length > 1 && messages.reduce((sum, message) => sum + message.text.length, 0) > 20000) {
    messages.splice(0, 2);
  }
  const controller = new AbortController();
  const timeout = setTimeout(() => controller.abort(), 55000);
  try {
    const response = await fetch('/api/chat', {
      method: 'POST', headers: { 'Content-Type': 'application/json', 'Authorization': 'Bearer ' + accessCode },
      body: JSON.stringify({ messages }), signal: controller.signal
    });
    const data = await response.json();
    if (!response.ok) {
      if (response.status === 401) $('#settings').showModal();
      throw Error(data.error || 'Yanıt alınamadı.');
    }
    history = [...messages, { role: 'assistant', text: data.answer }];
    lastAnswer = data.answer;
    bubble('assistant', data.answer);
    $('#message').value = '';
    $('#reply-actions').hidden = false;
    state('Yanıtınız hazır.');
    if ($('#auto-speak').checked) speak(data.answer);
  } catch (err) {
    // Keep the text in the composer so the user can retry without duplicate turns.
    userBubble.remove();
    error(err.name === 'AbortError' ? 'Yanıt zamanında gelmedi. Tekrar deneyebilirsiniz.' : err.message);
    state('Mesaj gönderilemedi.');
  } finally {
    clearTimeout(timeout);
    busy = false;
    controls();
  }
}

$('#chat-form').onsubmit = event => { event.preventDefault(); send(); };
$('#message').onkeydown = event => {
  if (event.key === 'Enter' && !event.shiftKey && !event.isComposing) { event.preventDefault(); send(); }
};
$('#settings-open').onclick = () => $('#settings').showModal();
$('#settings-save').onclick = () => { accessCode = $('#access-code').value.trim(); $('#access-code').value = ''; };
$('#read-reply').onclick = () => { if (lastAnswer) speak(lastAnswer); };
$('#stop-speech').onclick = () => { stopAudio(); state('Ses durduruldu.'); };
$('#clear').onclick = () => {
  stopAudio(); history = []; lastAnswer = ''; $('#message').value = '';
  $('#conversation').replaceChildren(); $('#reply-actions').hidden = true;
  error(''); state('Yeni sohbet. Hazır olduğunuzda konuşun.');
};
document.querySelectorAll('[data-prompt]').forEach(button => {
  button.onclick = () => { if (busy || listening) return; $('#message').value = button.dataset.prompt; $('#message').focus(); };
});

const Speech = window.SpeechRecognition || window.webkitSpeechRecognition;
if (Speech && window.isSecureContext) {
  recognition = new Speech();
  recognition.lang = 'tr-TR';
  recognition.interimResults = true;
  recognition.continuous = false;
  let before = '';
  let failed = false;
  recognition.onstart = () => { listening = true; controls(); state('Dinliyorum… Bitirince metni kontrol edin.', 'listening'); };
  recognition.onresult = event => {
    let transcript = '';
    for (let i = 0; i < event.results.length; i++) transcript += event.results[i][0].transcript + ' ';
    $('#message').value = (before + ' ' + transcript.trim()).trim().slice(0, 4000);
  };
  recognition.onend = () => {
    listening = false; controls();
    if (!failed) state('Metni kontrol edin, ardından gönder düğmesine dokunun.');
  };
  recognition.onerror = event => {
    failed = true;
    const descriptions = {
      'not-allowed': 'Mikrofon izni verilmedi. Safari’nin site ayarlarından izin verin veya klavyedeki dikte mikrofonunu kullanın.',
      'no-speech': 'Ses duyulmadı. Tekrar deneyin.',
      'audio-capture': 'Mikrofona erişilemedi.',
      'network': 'Konuşma hizmetine bağlanılamadı. Yazabilir veya iPhone klavyesindeki dikteyi kullanabilirsiniz.',
      'service-not-allowed': 'Konuşma hizmeti kullanılamıyor. iPhone klavyesindeki dikte mikrofonunu kullanabilirsiniz.'
    };
    error(descriptions[event.error] || 'Ses tanıma durdu. Yazılı mesaj gönderebilirsiniz.');
    state('Ses tanıma tamamlanamadı.');
  };
  $('#mic').onclick = () => {
    if (listening) { recognition.stop(); return; }
    stopAudio(); error(''); before = $('#message').value; failed = false;
    try { recognition.start(); } catch (_) { error('Mikrofon başlatılamadı. Biraz sonra tekrar deneyin.'); }
  };
} else {
  $('#speech-help').textContent = 'Ses tanıma için HTTPS bağlantısı ve destekleyen Safari sürümü gerekir. Mesaj alanına dokunup iPhone klavyesindeki dikte mikrofonunu da kullanabilirsiniz.';
}
document.addEventListener('visibilitychange', () => {
  if (document.hidden) { stopAudio(); if (recognition && listening) recognition.stop(); }
});
async function init() {
  try {
    const response = await fetch('/api/config');
    if (!response.ok) throw Error('Sunucuya ulaşılamadı.');
    const data = await response.json();
    ready = data.ai_ready;
    accessRequired = data.access_required;
    $('#connection').textContent = ready ? 'Yapay zekâ bağlantısı yapılandırıldı' : 'Ön izleme · Yapay zekâ bağlantısı bekleniyor';
    $('#setup-help').textContent = ready ? 'Sunucu yapılandırıldı. Bağlantı ilk mesajınızla doğrulanacak.' : 'Arayüz hazır. Gerçek yanıtlar için yönetici sunucuya Gemini API anahtarını eklemeli. Anahtarı sohbette paylaşmayın.';
  } catch (err) { error(err.message); $('#connection').textContent = 'Sunucu bağlantısı yok'; }
  controls();
}
init();
