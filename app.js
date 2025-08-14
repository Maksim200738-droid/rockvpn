const translations = {
  ru: {
    subscription: "Подписка",
    getLink: "Получить ссылку",
    expires: "Истекает через",
    install: "Установка",
    devicePC: "ПК",
    devicePhone: "Телефон",
    hiddify: "Hiddify",
    clash: "Clash Verge",
    downloadHiddify: "Скачайте Hiddify",
    downloadHiddifyDesc: "В главном разделе нажмите большую кнопку включения в центре для подключения к VPN. При необходимости выберите другой сервер в разделе Прокси.",
    downloadClash: "Скачайте Clash Verge",
    downloadClashDesc: "Скачайте и установите Clash Verge для вашей ОС.",
    windows: "Windows",
    macos: "macOS",
    linux: "Linux",
    serverSwitch: "Выбор/смена сервера",
    serverSwitchDesc: "После подключения, слева выберите 'Прокси' и выберите нужный сервер.",
    addSub: "Добавить подписку",
    addSubDesc: "Нажмите кнопку ниже, чтобы добавить подписку",
    addSubBtn: "Добавить подписку",
    importConfig: "Импортируйте конфиг",
    importConfigDesc: "Импортируйте полученную ссылку в Clash Verge.",
    ready: "Подключите и используйте",
    readyDesc: "В главном разделе нажмите большую кнопку включения в центре для подключения к VPN. Не забудьте выбрать сервер в списке серверов. При необходимости выберите другой сервер из списка серверов.",
    readyClashDesc: "В главном разделе нажмите большую кнопку включения для подключения к VPN. Не забудьте выбрать сервер в списке серверов.",
    copied: "Скопировано!",
    copyLink: "Скопировать ссылку"
  },
  en: {
    subscription: "Subscription",
    getLink: "Get Link",
    expires: "Expires in",
    install: "Setup",
    devicePC: "PC",
    devicePhone: "Phone",
    hiddify: "Hiddify",
    clash: "Clash Verge",
    downloadHiddify: "Download Hiddify",
    downloadHiddifyDesc: "In the main section, press the big power button in the center to connect to VPN. If needed, select another server in the Proxy section.",
    downloadClash: "Download Clash Verge",
    downloadClashDesc: "Download and install Clash Verge for your OS.",
    windows: "Windows",
    macos: "macOS",
    linux: "Linux",
    serverSwitch: "Server selection/switch",
    serverSwitchDesc: "After connecting, select 'Proxy' on the left and choose the desired server.",
    addSub: "Add subscription",
    addSubDesc: "Click the button below to add a subscription",
    addSubBtn: "Add subscription",
    importConfig: "Import config",
    importConfigDesc: "Import the received link into Clash Verge.",
    ready: "Connect and use",
    readyDesc: "In the main section, press the big power button in the center to connect to VPN. Don't forget to select a server from the server list. If needed, select another server from the list.",
    readyClashDesc: "In the main section, press the big power button to connect to VPN. Don't forget to select a server from the server list.",
    copied: "Copied!",
    copyLink: "Copy link"
  }
};

let currentLang = 'ru';

function setLang(lang) {
  currentLang = lang;
  document.documentElement.lang = lang;
  document.querySelectorAll('[data-i18n]').forEach(el => {
    const key = el.getAttribute('data-i18n');
    if (translations[lang][key]) {
      el.textContent = translations[lang][key];
    }
  });
  // Переводим select options
  document.querySelectorAll('.device-select option').forEach(opt => {
    const key = opt.getAttribute('data-i18n');
    if (translations[lang][key]) {
      opt.textContent = translations[lang][key];
    }
  });
  // Переводим шаги (если вкладка Clash Verge)
  const activeTab = document.querySelector('.install-tab.active');
  if (activeTab && activeTab.textContent.includes(translations['ru'].clash) || activeTab.textContent.includes(translations['en'].clash)) {
    renderClashSteps();
  } else {
    renderHiddifySteps();
  }
}

function renderHiddifySteps() {
  document.querySelector('.steps-vertical').innerHTML = `
    <div class='step-vert-line'></div>
    <div class='step-row'>
      <span class='step-icon step-download' data-tooltip='${translations[currentLang].downloadHiddify}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M12 7v7m0 0l-3-3m3 3l3-3' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='downloadHiddify'>${translations[currentLang].downloadHiddify}</div>
        <div class='step-desc' data-i18n='downloadHiddifyDesc'>${translations[currentLang].downloadHiddifyDesc}</div>
        <div class='os-btns'>
          <a href='#' class='os-btn'><span class='os-ico win' data-tooltip='Windows'></span><span data-i18n='windows'>${translations[currentLang].windows}</span></a>
          <a href='#' class='os-btn'><span class='os-ico mac' data-tooltip='macOS'></span><span data-i18n='macos'>${translations[currentLang].macos}</span></a>
          <a href='#' class='os-btn'><span class='os-ico lin' data-tooltip='Linux'></span><span data-i18n='linux'>${translations[currentLang].linux}</span></a>
        </div>
      </div>
    </div>
    <div class='step-row'>
      <span class='step-icon step-info' data-tooltip='Info'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><text x='12' y='16' text-anchor='middle' font-size='14' fill='#fff' font-family='Arial' font-weight='bold'>i</text></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='serverSwitch'>${translations[currentLang].serverSwitch}</div>
        <div class='step-desc' data-i18n='serverSwitchDesc'>${translations[currentLang].serverSwitchDesc}</div>
      </div>
    </div>
    <div class='step-row'>
      <span class='step-icon step-plus' data-tooltip='${translations[currentLang].addSub}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M12 8v8M8 12h8' stroke='#fff' stroke-width='2' stroke-linecap='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='addSub'>${translations[currentLang].addSub}</div>
        <div class='step-desc' data-i18n='addSubDesc'>${translations[currentLang].addSubDesc}</div>
        <button class='add-sub-btn' data-i18n='addSubBtn'>${translations[currentLang].addSubBtn}</button>
      </div>
    </div>
    <div class='step-row'>
      <span class='step-icon step-check' data-tooltip='${translations[currentLang].ready}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M8 12.5l2.5 2.5 5-5' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='ready'>${translations[currentLang].ready}</div>
        <div class='step-desc' data-i18n='readyDesc'>${translations[currentLang].readyDesc}</div>
      </div>
    </div>
  `;
  addCopyHandlers();
}

function renderClashSteps() {
  document.querySelector('.steps-vertical').innerHTML = `
    <div class='step-vert-line'></div>
    <div class='step-row'>
      <span class='step-icon step-download' data-tooltip='${translations[currentLang].downloadClash}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M12 7v7m0 0l-3-3m3 3l3-3' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='downloadClash'>${translations[currentLang].downloadClash}</div>
        <div class='step-desc' data-i18n='downloadClashDesc'>${translations[currentLang].downloadClashDesc}</div>
        <div class='os-btns'>
          <a href='#' class='os-btn'><span class='os-ico win' data-tooltip='Windows'></span><span data-i18n='windows'>${translations[currentLang].windows}</span></a>
          <a href='#' class='os-btn'><span class='os-ico mac' data-tooltip='macOS'></span><span data-i18n='macos'>${translations[currentLang].macos}</span></a>
          <a href='#' class='os-btn'><span class='os-ico lin' data-tooltip='Linux'></span><span data-i18n='linux'>${translations[currentLang].linux}</span></a>
        </div>
      </div>
    </div>
    <div class='step-row'>
      <span class='step-icon step-plus' data-tooltip='${translations[currentLang].importConfig}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M12 8v8M8 12h8' stroke='#fff' stroke-width='2' stroke-linecap='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='importConfig'>${translations[currentLang].importConfig}</div>
        <div class='step-desc' data-i18n='importConfigDesc'>${translations[currentLang].importConfigDesc}</div>
        <button class='add-sub-btn' data-i18n='copyLink'>${translations[currentLang].copyLink}</button>
      </div>
    </div>
    <div class='step-row'>
      <span class='step-icon step-check' data-tooltip='${translations[currentLang].ready}'>
        <svg width='24' height='24' fill='none'><circle cx='12' cy='12' r='12' fill='#00c6fb'/><path d='M8 12.5l2.5 2.5 5-5' stroke='#fff' stroke-width='2' stroke-linecap='round' stroke-linejoin='round'/></svg>
      </span>
      <div class='step-content'>
        <div class='step-title' data-i18n='ready'>${translations[currentLang].ready}</div>
        <div class='step-desc' data-i18n='readyClashDesc'>${translations[currentLang].readyClashDesc}</div>
      </div>
    </div>
  `;
  addCopyHandlers();
}

function addCopyHandlers() {
  document.querySelectorAll('.add-sub-btn, .sub-link-btn').forEach(btn => {
    btn.onclick = function() {
      const key = document.getElementById('vpn-key').textContent;
      navigator.clipboard.writeText(key);
      btn.textContent = translations[currentLang].copied;
      setTimeout(() => {
        btn.textContent = btn.classList.contains('add-sub-btn') ? translations[currentLang][btn.getAttribute('data-i18n')] : translations[currentLang].getLink;
      }, 1200);
    };
  });
}

window.onload = function() {
  // Динамическая подстановка ключа и срока
  let key = new URLSearchParams(window.location.search).get('key') || 'nit8e67o';
  let expires = new URLSearchParams(window.location.search).get('expires') || '4 дня';
  document.getElementById('vpn-key').textContent = key;
  document.getElementById('expires-in').textContent = expires;

  // QR-код
  let qr = new QRious({
    element: document.getElementById('qr-canvas'),
    value: key,
    size: 64,
    background: 'white',
    foreground: '#23272f',
    level: 'H'
  });

  // Копирование ключа (и кнопка, и "добавить подписку")
  addCopyHandlers();

  // Переключение вкладок
  const tabs = document.querySelectorAll('.install-tab');
  tabs.forEach(tab => {
    tab.addEventListener('click', function() {
      tabs.forEach(t => t.classList.remove('active'));
      this.classList.add('active');
      if (this.textContent.includes(translations['ru'].clash) || this.textContent.includes(translations['en'].clash)) {
        renderClashSteps();
      } else {
        renderHiddifySteps();
      }
      setLang(currentLang); // Перевести новые элементы
    });
  });

  // Смена устройства (ПК/Телефон)
  document.querySelector('.device-select').addEventListener('change', function() {
    // Можно добавить логику для мобильных инструкций, если нужно
  });

  // Смена языка (Русский/English)
  document.querySelector('.lang-btn').addEventListener('click', function() {
    const btn = this;
    if (btn.querySelector('.lang-txt').textContent === 'Русский') {
      btn.querySelector('.lang-txt').textContent = 'English';
      btn.querySelector('.lang-flag').textContent = '🇬🇧';
      setLang('en');
    } else {
      btn.querySelector('.lang-txt').textContent = 'Русский';
      btn.querySelector('.lang-flag').textContent = '🇷🇺';
      setLang('ru');
    }
  });

  setLang(currentLang);
}; 