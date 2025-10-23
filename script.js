// Получаем видео элемент
const video = document.getElementById('mainVideo');

// Настройка зацикливания последних 2 секунд
video.addEventListener('loadedmetadata', function() {
  const loopStartTime = video.duration - 2; // Последние 2 секунды
  
  // Автозапуск видео
  video.play().catch(err => {
    console.log('Автозапуск заблокирован браузером:', err);
  });
  
  // Отслеживание времени и создание loop
  video.addEventListener('timeupdate', function() {
    // Когда достигли конца, возвращаемся к началу loop-сегмента
    if (video.currentTime >= video.duration - 0.1) {
      video.currentTime = loopStartTime;
      video.play();
    }
  });
});

// Управление видео при инициализации Reveal.js
Reveal.on('ready', event => {
  console.log('Презентация готова!');
  // Повторная попытка запуска видео
  video.play().catch(err => {
    console.log('Нужно кликнуть на экран для запуска видео');
  });
});
