// Основной JavaScript файл для приложения "Молодежный сленг"

document.addEventListener('DOMContentLoaded', function() {
    console.log('Slang Database App loaded');
    
    // Автоматическое скрытие alert через 5 секунд
    const alerts = document.querySelectorAll('.alert:not(.alert-permanent)');
    alerts.forEach(function(alert) {
        setTimeout(function() {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000);
    });

    // Подтверждение удаления
    const deleteForms = document.querySelectorAll('form[data-confirm]');
    deleteForms.forEach(function(form) {
        form.addEventListener('submit', function(e) {
            if (!confirm(this.dataset.confirm || 'Вы уверены?')) {
                e.preventDefault();
            }
        });
    });

    // Поиск в реальном времени (опционально)
    const searchInput = document.querySelector('input[name="q"]');
    if (searchInput) {
        let timeout = null;
        searchInput.addEventListener('input', function() {
            clearTimeout(timeout);
            timeout = setTimeout(function() {
                fetchSuggestions(searchInput.value);
            }, 300);
        });
    }
    
    // Подсветка активного пункта меню
    const currentPath = window.location.pathname;
    document.querySelectorAll('.navbar-nav .nav-link').forEach(function(link) {
        if (link.getAttribute('href') === currentPath) {
            link.classList.add('active');
        }
    });
    
    // Обновить счётчик избранных
    updateFavCount();
    
    // Подсветка кнопок избранного на странице
    highlightFavoriteButtons();
});

// Поиск предложений (autocomplete)
function fetchSuggestions(query) {
    if (query.length < 2) return;
    
    fetch(`/api/search?q=${encodeURIComponent(query)}`)
        .then(response => response.json())
        .then(data => {
            console.log('Suggestions:', data);
        })
        .catch(error => console.error('Error:', error));
}

// Получить список избранных
function getFavorites() {
    return JSON.parse(localStorage.getItem('favorites') || '[]');
}

// Сохранить список избранных
function saveFavorites(favorites) {
    localStorage.setItem('favorites', JSON.stringify(favorites));
    updateFavCount();
    highlightFavoriteButtons();
}

// Экспорт избранного в файл
function exportFavorites() {
    const favorites = getFavorites();
    if (favorites.length === 0) {
        showNotification('Нет избранных слов для экспорта', 'warning');
        return;
    }
    
    const dataStr = JSON.stringify(favorites, null, 2);
    const blob = new Blob([dataStr], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = 'favorites.json';
    link.click();
    showNotification('Избранное экспортировано!', 'success');
}

// Импорт избранного из файла
function importFavorites(file) {
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const imported = JSON.parse(e.target.result);
            if (Array.isArray(imported)) {
                const current = getFavorites();
                const merged = [...new Set([...current, ...imported])];
                saveFavorites(merged);
                showNotification(`Импортировано ${imported.length} слов`, 'success');
                setTimeout(() => location.reload(), 1000);
            }
        } catch (err) {
            showNotification('Ошибка импорта: неверный формат', 'danger');
        }
    };
    reader.readAsText(file);
}

// Добавить/удалить из избранного
function toggleFavorite(wordId) {
    const favorites = getFavorites();
    const index = favorites.indexOf(wordId);
    
    if (index > -1) {
        // Удалить
        favorites.splice(index, 1);
        showNotification('Удалено из избранного', 'info');
    } else {
        // Добавить
        favorites.push(wordId);
        showNotification('Добавлено в избранное', 'success');
    }
    
    saveFavorites(favorites);
    
    // Если мы на странице избранного, перезагрузить
    if (window.location.pathname === '/favorites') {
        setTimeout(() => location.reload(), 500);
    }
}

// Обновить счётчик избранных
function updateFavCount() {
    const favorites = getFavorites();
    const count = favorites.length;
    
    const badge = document.getElementById('fav-count');
    if (badge) {
        badge.textContent = count;
        badge.style.display = count > 0 ? 'inline-block' : 'none';
    }
}

// Подсветить кнопки избранного на странице
function highlightFavoriteButtons() {
    const favorites = getFavorites();
    
    document.querySelectorAll('[data-fav-toggle]').forEach(btn => {
        const wordId = parseInt(btn.dataset.favToggle);
        if (favorites.includes(wordId)) {
            btn.classList.add('text-danger');
            btn.innerHTML = '<i class="bi bi-heart-fill"></i>';
        } else {
            btn.classList.remove('text-danger');
            btn.innerHTML = '<i class="bi bi-heart"></i>';
        }
    });
}

// Голосование за слово (localStorage)
function vote(wordId, voteType) {
    // Проверяем, не голосовали ли уже
    const votes = JSON.parse(localStorage.getItem('votes') || '{}');
    const previousVote = votes[wordId];
    
    // Если уже голосовали так же - убираем голос
    if (previousVote === voteType) {
        delete votes[wordId];
        localStorage.setItem('votes', JSON.stringify(votes));
        
        // Обновляем счётчик
        const scoreElement = document.getElementById(`vote-score-${wordId}`);
        if (scoreElement) {
            const current = parseInt(scoreElement.textContent) || 0;
            scoreElement.textContent = current - voteType;
        }
        showNotification('Голос отменён', 'info');
        return;
    }
    
    // Запоминаем голос
    votes[wordId] = voteType;
    localStorage.setItem('votes', JSON.stringify(votes));
    
    // Отправляем на сервер
    fetch('/api/vote', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            word_id: wordId,
            vote_type: voteType
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            const scoreElement = document.getElementById(`vote-score-${wordId}`);
            if (scoreElement) {
                scoreElement.textContent = data.new_popularity;
            }
            
            // Подсветка кнопок
            document.querySelectorAll(`[data-vote="${wordId}"]`).forEach(btn => {
                btn.classList.remove('active', 'btn-success', 'btn-danger');
            });
            const activeBtn = document.querySelector(`[data-vote="${wordId}"][data-vote-type="${voteType}"]`);
            if (activeBtn) {
                activeBtn.classList.add('active', voteType === 1 ? 'btn-success' : 'btn-danger');
            }
            
            showNotification('Голос учтён!', 'success');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showNotification('Ошибка голосования', 'danger');
    });
}

// Показать уведомление
function showNotification(message, type = 'info') {
    const container = document.querySelector('.container');
    if (!container) return;
    
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `${message}<button type="button" class="btn-close" data-bs-dismiss="alert"></button>`;
    
    container.insertBefore(alert, container.firstChild);
    
    setTimeout(function() {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 3000);
}

// Экспорт данных
function exportData(format) {
    const url = format === 'csv' ? '/export/csv' : '/export/json';
    window.open(url, '_blank');
}

// Копирование текста в буфер
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        showNotification('Скопировано в буфер!', 'success');
    });
}

// Форматирование даты
function formatDate(dateString) {
    return new Date(dateString).toLocaleDateString('ru-RU', {
        year: 'numeric', month: 'long', day: 'numeric'
    });
}

// Экспорт статистики в JSON
function exportStatistics() {
    fetch('/api/statistics')
        .then(response => response.json())
        .then(data => {
            const dataStr = JSON.stringify(data, null, 2);
            const blob = new Blob([dataStr], {type: 'application/json'});
            const url = URL.createObjectURL(blob);
            const link = document.createElement('a');
            link.href = url;
            link.download = 'slang_statistics.json';
            link.click();
        });
}