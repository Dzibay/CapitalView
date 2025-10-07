<template>
  <aside class="sidebar">
    <div class="sidebar-header">
      <h1 class="logo">InvestTrack</h1>
    </div>
    <nav class="sidebar-nav">
      <ul>
        <li class="active">
          <a href="#">
            <svg viewBox="0 0 24 24"><path d="M10 20v-6h4v6h5v-8h3L12 3 2 12h3v8z"></path></svg>
            <span>Главная</span>
          </a>
        </li>
        <li>
          <a href="#">
            <svg viewBox="0 0 24 24"><path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"></path></svg>
            <span>Аналитика</span>
          </a>
        </li>
        <li>
          <a href="#">
            <svg viewBox="0 0 24 24"><path d="M14 10H2v2h12v-2zm0-4H2v2h12V6zm4 8v-4h-2v4h-4v2h4v4h2v-4h4v-2h-4zM2 16h8v-2H2v2z"></path></svg>
            <span>Сделки</span>
          </a>
        </li>
        <li>
          <a href="#">
            <svg viewBox="0 0 24 24"><path d="M12 22c1.1 0 2-.9 2-2h-4c0 1.1.9 2 2 2zm6-6v-5c0-3.07-1.63-5.64-4.5-6.32V4c0-.83-.67-1.5-1.5-1.5s-1.5.67-1.5 1.5v.68C7.64 5.36 6 7.92 6 11v5l-2 2v1h16v-1l-2-2z"></path></svg>
            <span>Уведомления</span>
          </a>
        </li>
      </ul>
    </nav>
    <div class="sidebar-footer">
      <a href="#" class="footer-link">
        <svg viewBox="0 0 24 24"><path d="M19.43 12.98c.04-.32.07-.64.07-.98s-.03-.66-.07-.98l2.11-1.65c.19-.15.24-.42.12-.64l-2-3.46c-.12-.22-.39-.3-.61-.22l-2.49 1c-.52-.4-1.08-.73-1.69-.98l-.38-2.65C14.46 2.18 14.25 2 14 2h-4c-.25 0-.46.18-.49.42l-.38 2.65c-.61.25-1.17.59-1.69.98l-2.49-1c-.23-.09-.49 0-.61.22l-2 3.46c-.13.22-.07.49.12.64l2.11 1.65c-.04.32-.07.65-.07.98s.03.66.07.98l-2.11 1.65c-.19.15-.24.42-.12.64l2 3.46c.12.22.39.3.61.22l2.49-1c.52.4 1.08.73 1.69.98l.38 2.65c.03.24.24.42.49.42h4c.25 0 .46-.18.49-.42l.38-2.65c.61-.25 1.17-.59 1.69-.98l2.49 1c.23.09.49 0 .61-.22l2-3.46c.12-.22.07-.49-.12-.64l-2.11-1.65zM12 15.5c-1.93 0-3.5-1.57-3.5-3.5s1.57-3.5 3.5-3.5 3.5 1.57 3.5 3.5-1.57 3.5-3.5 3.5z"></path></svg>
        <span>Настройки</span>
      </a>
      <a href="#" class="footer-link">
        <svg viewBox="0 0 24 24"><path d="M10.09 15.59L11.5 17l5-5-5-5-1.41 1.41L12.67 11H3v2h9.67l-2.58 2.59zM19 3H5c-1.11 0-2 .9-2 2v4h2V5h14v14H5v-4H3v4c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"></path></svg>
        <span>Выход</span>
      </a>
    </div>
  </aside>
</template>

<style scoped>
.sidebar {
  width: 260px;
  background-color: #111827;
  color: #d1d5db;
  display: flex;
  flex-direction: column;
  height: 100vh;
  position: fixed;
  left: 0;
  top: 0;
  transition: transform 0.3s ease-in-out;
}
.sidebar-header {
  padding: 1.5rem;
  border-bottom: 1px solid #374151;
}
.logo {
  font-size: 1.5rem;
  font-weight: bold;
  color: #fff;
  text-align: center;
}
.sidebar-nav {
  flex-grow: 1;
  padding: 1rem 0;
}
.sidebar-nav ul {
  list-style: none;
  padding: 0;
  margin: 0;
}
.sidebar-nav li a {
  display: flex;
  align-items: center;
  padding: 0.75rem 1.5rem;
  color: #d1d5db;
  text-decoration: none;
  transition: background-color 0.2s;
  border-left: 3px solid transparent;
}
.sidebar-nav li a:hover {
  background-color: #374151;
}
.sidebar-nav li.active a {
  background-color: #4A55A2;
  color: #fff;
  border-left-color: #A0BFE0;
}
.sidebar-nav svg {
  width: 24px;
  height: 24px;
  margin-right: 1rem;
  fill: currentColor;
}
.sidebar-footer {
  padding: 1rem 1.5rem;
  border-top: 1px solid #374151;
}
.footer-link {
  display: flex;
  align-items: center;
  color: #d1d5db;
  text-decoration: none;
  padding: 0.5rem 0;
}
.footer-link:hover {
  color: #fff;
}
.footer-link svg {
  width: 20px;
  height: 20px;
  margin-right: 1rem;
  fill: currentColor;
}
</style>