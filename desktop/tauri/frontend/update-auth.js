const form = document.getElementById('authorization');
const token = document.getElementById('token');
const statusMessage = document.getElementById('status');
const buttons = form.querySelectorAll('button');

async function setAuthorization(value) {
  token.value = '';
  buttons.forEach(button => { button.disabled = true; });
  statusMessage.textContent = value ? '正在验证仓库访问权限…' : '正在移除授权…';
  try {
    await window.__TAURI__.core.invoke('set_update_token', { token: value });
    statusMessage.textContent = value ? '已保存到系统凭据库，正在检查更新。' : '已移除更新授权。';
  } catch (error) {
    statusMessage.textContent = typeof error === 'string' ? error : '无法设置更新授权。';
  } finally {
    buttons.forEach(button => { button.disabled = false; });
  }
}

form.addEventListener('submit', event => {
  event.preventDefault();
  const value = token.value.trim();
  if (value) setAuthorization(value);
});
document.getElementById('clear').addEventListener('click', () => setAuthorization(null));
