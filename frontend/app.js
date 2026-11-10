'use strict';

const $ = (id) => document.getElementById(id);
const state = { token: sessionStorage.getItem('margin-token'), user: null, page: 1, search: '', total: 0, selected: null, editing: null, afterLogin: false, request: 0 };
const limit = 6;
let searchTimer, toastTimer;

function words(content) { return content.trim() ? content.trim().split(/\s+/).length : 0; }
function readTime(content) { return `${Math.max(1, Math.ceil(words(content) / 200))} min read`; }
function notify(message) {
  $('toast').textContent = message;
  $('toast').hidden = false;
  clearTimeout(toastTimer);
  toastTimer = setTimeout(() => { $('toast').hidden = true; }, 4500);
}
function syncAuth() {
  $('login-button').hidden = Boolean(state.token);
  $('register-button').hidden = Boolean(state.token);
  $('logout-button').hidden = !state.token;
  $('logout-button').title = state.user ? `Signed in as ${state.user.username}` : 'Sign out';
  $('reader-actions').hidden = !(state.user && state.selected && (state.user.is_admin || state.selected.owner_id === state.user.id));
}
function signOut() {
  state.token = null;
  state.user = null;
  sessionStorage.removeItem('margin-token');
  syncAuth();
}
async function api(path, options = {}) {
  const headers = new Headers(options.headers);
  if (state.token) headers.set('Authorization', `Bearer ${state.token}`);
  let response;
  try { response = await fetch(path, { ...options, headers }); }
  catch { throw new Error('Cannot reach the server. Check your connection and try again.'); }
  const data = await response.json().catch(() => ({}));
  if (!response.ok) {
    if (response.status === 401 && path !== '/login') signOut();
    const detail = data.detail;
    throw new Error(Array.isArray(detail) ? detail.map((item) => `${item.loc.at(-1)}: ${item.msg}`).join('. ') : detail || 'Something went wrong. Please try again.');
  }
  return data;
}
function node(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function card(post) {
  const article = node('article', 'post-card');
  const art = node('button', `card-art art-${post.id % 4}`);
  art.setAttribute('aria-label', `Read ${post.title}`);
  const shape = node('span', 'shape');
  shape.setAttribute('aria-hidden', 'true');
  art.append(shape);
  art.onclick = () => openStory(post.id);
  const label = node('div', 'card-label');
  label.append(node('span', '', 'PERSPECTIVES'), node('span', '', readTime(post.content).toUpperCase()));
  const title = node('button', 'post-title', post.title);
  title.onclick = () => openStory(post.id);
  const heading = node('h3');
  heading.style.margin = '0';
  heading.append(title);
  const excerpt = node('p', 'excerpt', post.content);
  const bottom = node('div', 'card-bottom');
  const arrow = node('button', '', '↗');
  arrow.setAttribute('aria-label', `Open ${post.title}`);
  arrow.onclick = () => openStory(post.id);
  bottom.append(node('span', 'avatar', 'm.'), node('span', '', post.author), arrow);
  article.append(art, label, heading, excerpt, bottom);
  return article;
}
async function loadPosts() {
  const request = ++state.request;
  $('posts').setAttribute('aria-busy', 'true');
  $('posts').replaceChildren(...Array.from({ length: 3 }, () => node('div', 'skeleton')));
  $('empty-state').hidden = true;
  $('error-state').hidden = true;
  $('pagination').hidden = true;
  $('results-label').textContent = 'Loading stories…';
  try {
    const data = await api(`/blogs?${new URLSearchParams({ page: state.page, limit, search: state.search })}`);
    if (request !== state.request) return;
    state.total = data.total;
    if (state.page > 1 && !data.data.length) { state.page = Math.max(1, Math.ceil(data.total / limit)); return loadPosts(); }
    $('posts').replaceChildren(...data.data.map(card));
    $('results-label').textContent = `${data.total} ${data.total === 1 ? 'story' : 'stories'}${state.search ? ` matching “${state.search}”` : ' in the journal'}`;
    $('empty-state').hidden = data.total !== 0;
    $('empty-state').querySelector('h3').textContent = state.search ? 'No stories found.' : 'A little space for your first story.';
    $('empty-state').querySelector('p').textContent = state.search ? 'Try a different title or clear your search to explore the journal.' : 'Every great journal starts with a single thought. Make this one yours.';
    $('empty-write').hidden = Boolean(state.search);
    const pages = Math.ceil(data.total / limit);
    $('pagination').hidden = pages <= 1;
    $('page-label').textContent = `Page ${state.page} of ${pages}`;
    $('previous').disabled = state.page <= 1;
    $('next').disabled = state.page >= pages;
  } catch (error) {
    if (request !== state.request) return;
    $('posts').replaceChildren();
    $('results-label').textContent = 'Journal unavailable';
    $('load-error').textContent = error.message;
    $('error-state').hidden = false;
  } finally {
    if (request === state.request) $('posts').setAttribute('aria-busy', 'false');
  }
}
function showLogin(writeAfter = false) {
  state.afterLogin = writeAfter;
  $('login-error').textContent = '';
  $('login-dialog').showModal();
}
function showRegister() {
  $('register-error').textContent = '';
  $('register-dialog').showModal();
}
function acceptSession(data) {
  state.token = data.access_token;
  state.user = data.user;
  sessionStorage.setItem('margin-token', state.token);
  syncAuth();
}
function updateWordCount() {
  const content = $('post-content').value;
  $('word-count').textContent = `${words(content)} words · ${readTime(content)}`;
}
function openEditor(post = null) {
  if (!state.token) { showLogin(true); return; }
  state.editing = post?.id ?? null;
  $('editor-heading').textContent = post ? 'Refine your perspective.' : 'A new perspective.';
  $('post-title').value = post?.title ?? '';
  $('post-content').value = post?.content ?? '';
  $('publish-button').textContent = post ? 'Save changes ↗' : 'Publish story ↗';
  $('editor-error').textContent = '';
  updateWordCount();
  $('editor-dialog').showModal();
}
async function openStory(id) {
  try {
    const post = await api(`/blogs/${id}`);
    state.selected = post;
    $('reader-title').textContent = post.title;
    $('reader-content').textContent = post.content;
    $('reader-time').textContent = readTime(post.content);
    $('reader-author').textContent = post.author;
    syncAuth();
    $('reader-dialog').showModal();
  } catch (error) { notify(error.message); }
}

for (const button of document.querySelectorAll('[data-close]')) button.addEventListener('click', () => button.closest('dialog').close());
for (const dialog of document.querySelectorAll('dialog')) dialog.addEventListener('click', (event) => {
  if (event.target === dialog) {
    const rect = dialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) dialog.close();
  }
});
for (const id of ['write-button', 'empty-write', 'about-write']) $(id).onclick = () => openEditor();
$('login-button').onclick = () => showLogin();
$('register-button').onclick = () => { state.afterLogin = false; showRegister(); };
$('show-register').onclick = () => { $('login-dialog').close(); showRegister(); };
$('show-login').onclick = () => { $('register-dialog').close(); showLogin(state.afterLogin); };
$('logout-button').onclick = () => { signOut(); notify('You have signed out.'); };
$('login-form').onsubmit = async (event) => {
  event.preventDefault();
  const submit = event.submitter;
  submit.disabled = true;
  submit.textContent = 'Signing in…';
  $('login-error').textContent = '';
  try {
    const form = new FormData(event.target);
    const data = await api('/login', { method: 'POST', body: new URLSearchParams(form) });
    acceptSession(data);
    $('login-dialog').close();
    $('login-form').reset();
    notify('Welcome back. Your writing space is ready.');
    if (state.afterLogin) openEditor();
  } catch (error) { $('login-error').textContent = error.message; }
  finally { submit.disabled = false; submit.textContent = 'Sign in ↗'; }
};
$('register-form').onsubmit = async (event) => {
  event.preventDefault();
  const form = new FormData(event.target);
  $('register-error').textContent = '';
  if (form.get('password') !== form.get('confirm')) {
    $('register-error').textContent = 'Your passwords do not match.';
    return;
  }
  const submit = event.submitter;
  submit.disabled = true;
  submit.textContent = 'Creating account…';
  try {
    const data = await api('/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ username: form.get('username'), password: form.get('password') }) });
    acceptSession(data);
    $('register-dialog').close();
    $('register-form').reset();
    notify(`Welcome, ${data.user.username}. Your account is ready.`);
    if (state.afterLogin) openEditor();
  } catch (error) { $('register-error').textContent = error.message; }
  finally { submit.disabled = false; submit.textContent = 'Create account ↗'; }
};
$('editor-form').onsubmit = async (event) => {
  event.preventDefault();
  const title = $('post-title').value.trim();
  const content = $('post-content').value.trim();
  if (!title || !content) { $('editor-error').textContent = 'Please add both a title and a story.'; return; }
  const submit = $('publish-button');
  submit.disabled = true;
  submit.textContent = 'Saving…';
  $('editor-error').textContent = '';
  const editing = state.editing;
  try {
    await api(editing === null ? '/blogs' : `/blogs/${editing}`, { method: editing === null ? 'POST' : 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ title, content }) });
    $('editor-dialog').close();
    if (editing === null) { state.page = 1; state.search = ''; $('search').value = ''; }
    await loadPosts();
    notify(editing === null ? 'Your story is published. A new perspective, shared.' : 'Your story has been updated.');
  } catch (error) { $('editor-error').textContent = error.message; }
  finally { submit.disabled = false; submit.textContent = editing === null ? 'Publish story ↗' : 'Save changes ↗'; }
};
$('post-content').oninput = updateWordCount;
$('edit-button').onclick = () => { $('reader-dialog').close(); openEditor(state.selected); };
$('delete-button').onclick = () => { $('delete-error').textContent = ''; $('delete-dialog').showModal(); };
$('confirm-delete').onclick = async () => {
  $('confirm-delete').disabled = true;
  try {
    await api(`/blogs/${state.selected.id}`, { method: 'DELETE' });
    $('delete-dialog').close();
    $('reader-dialog').close();
    state.selected = null;
    await loadPosts();
    notify('Story deleted. Space for something new.');
  } catch (error) { $('delete-error').textContent = error.message; }
  finally { $('confirm-delete').disabled = false; }
};
function search() { clearTimeout(searchTimer); state.search = $('search').value.trim(); state.page = 1; loadPosts(); }
$('search-form').onsubmit = (event) => { event.preventDefault(); search(); };
$('search').oninput = () => { clearTimeout(searchTimer); searchTimer = setTimeout(search, 300); };
$('retry-button').onclick = loadPosts;
for (const [id, direction] of [['previous', -1], ['next', 1]]) $(id).onclick = () => { state.page += direction; loadPosts(); $('journal').scrollIntoView({ behavior: 'smooth' }); };
document.addEventListener('keydown', (event) => {
  if (event.key === '/' && !['INPUT', 'TEXTAREA'].includes(document.activeElement.tagName) && !document.querySelector('dialog[open]')) { event.preventDefault(); $('search').focus(); }
});
$('year').textContent = new Date().getFullYear();
syncAuth();
async function initialize() {
  if (state.token) {
    try { state.user = await api('/me'); syncAuth(); }
    catch (error) { notify(error.message); }
  }
  await loadPosts();
}
initialize();
