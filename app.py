from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, send_file
from models import db, Word, Period, Category, Source, User, Tag, Comment, Vote, word_tags
from config import Config
from sqlalchemy import func, desc, or_, and_
from datetime import datetime
import json
import csv
import io

app = Flask(__name__)
app.config.from_object(Config)

db.init_app(app)

# Главная страница
@app.route('/')
def index():
    recent_words = Word.query.order_by(desc(Word.created_at)).limit(6).all()
    periods = Period.query.all()
    categories = Category.query.all()
    total_words = Word.query.count()
    
    # Случайное слово для главной
    random_word = Word.query.order_by(func.random()).first()
    
    return render_template('index.html', 
                         recent_words=recent_words, 
                         periods=periods,
                         categories=categories,
                         total_words=total_words,
                         random_word=random_word)


# Случайное слово
@app.route('/random')
def random_word():
    """Перенаправляет на случайное слово."""
    word = Word.query.order_by(func.random()).first()
    if word:
        return redirect(url_for('word_detail', word_id=word.id))
    return redirect(url_for('index'))

# Поиск слов
@app.route('/search')
def search():
    query = request.args.get('q', '')
    period_id = request.args.get('period', type=int)
    category_id = request.args.get('category', type=int)
    sort_by = request.args.get('sort', 'word')
    page = request.args.get('page', 1, type=int)
    
    words_query = Word.query
    
    if query:
        words_query = words_query.filter(
            db.or_(
                Word.word.ilike(f'%{query}%'),
                Word.meaning.ilike(f'%{query}%'),
                Word.synonyms.ilike(f'%{query}%')
            )
        )
    
    if period_id:
        words_query = words_query.filter(Word.period_id == period_id)
    
    if category_id:
        words_query = words_query.filter(Word.category_id == category_id)
    
    if sort_by == 'word':
        words_query = words_query.order_by(Word.word)
    elif sort_by == 'popularity':
        words_query = words_query.order_by(desc(Word.popularity))
    elif sort_by == 'created':
        words_query = words_query.order_by(desc(Word.created_at))
    
    # Пагинация: 12 слов на страницу
    pagination = words_query.paginate(page=page, per_page=12, error_out=False)
    words = pagination.items
    
    periods = Period.query.all()
    categories = Category.query.all()
    
    # Популярные теги
    popular_tags = Tag.query.order_by(Tag.name).limit(10).all()
    
    return render_template('search.html', 
                         words=words, 
                         query=query,
                         periods=periods,
                         categories=categories,
                         selected_period=period_id,
                         selected_category=category_id,
                         sort_by=sort_by,
                         count=pagination.total,
                         pagination=pagination,
                         page=page,
                         popular_tags=popular_tags)

# Детальная информация о слове
@app.route('/word/<int:word_id>')
def word_detail(word_id):
    word = Word.query.get_or_404(word_id)
    return render_template('word_detail.html', word=word)

# Добавление нового слова
@app.route('/add', methods=['GET', 'POST'])
def add_word():
    if request.method == 'POST':
        word_text = request.form.get('word', '').strip()
        meaning = request.form.get('meaning', '').strip()
        period_id = request.form.get('period_id', type=int)
        category_id = request.form.get('category_id', type=int)
        origin = request.form.get('origin', '').strip()
        example = request.form.get('example', '').strip()
        popularity = request.form.get('popularity', 0, type=int)
        synonyms = request.form.get('synonyms', '').strip()
        antonyms = request.form.get('antonyms', '').strip()
        usage_frequency = request.form.get('usage_frequency', 5, type=int)
        is_verified = request.form.get('is_verified') == 'on'
        tags_str = request.form.get('tags', '').strip()
        
        if not word_text or not meaning:
            flash('Слово и значение обязательны для заполнения!', 'danger')
            return redirect(url_for('add_word'))
        
        new_word = Word(
            word=word_text,
            meaning=meaning,
            period_id=period_id,
            category_id=category_id,
            origin=origin,
            example=example,
            popularity=popularity,
            synonyms=synonyms,
            antonyms=antonyms,
            usage_frequency=usage_frequency,
            is_verified=is_verified
        )
        
        try:
            db.session.add(new_word)
            db.session.flush()  # Чтобы получить ID перед коммитом
            
            # Добавляем теги
            if tags_str:
                tag_names = [t.strip() for t in tags_str.split(',')]
                for tag_name in tag_names:
                    if tag_name:
                        tag = Tag.query.filter_by(name=tag_name).first()
                        if not tag:
                            tag = Tag(name=tag_name)
                            db.session.add(tag)
                        new_word.tags.append(tag)
            
            db.session.commit()
            flash(f'Слово "{word_text}" успешно добавлено!', 'success')
            return redirect(url_for('word_detail', word_id=new_word.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при добавлении: {str(e)}', 'danger')
    
    periods = Period.query.all()
    categories = Category.query.all()
    return render_template('add_word.html', periods=periods, categories=categories)

# Редактирование слова
@app.route('/word/<int:word_id>/edit', methods=['GET', 'POST'])
def edit_word(word_id):
    word = Word.query.get_or_404(word_id)
    
    if request.method == 'POST':
        # Сохраняем старые значения для истории
        old_values = {
            'word': word.word,
            'meaning': word.meaning,
            'period_id': word.period_id,
            'category_id': word.category_id,
        }
        
        # Обновляем значения
        word.word = request.form.get('word', '').strip()
        word.meaning = request.form.get('meaning', '').strip()
        word.period_id = request.form.get('period_id', type=int)
        word.category_id = request.form.get('category_id', type=int)
        word.origin = request.form.get('origin', '').strip()
        word.example = request.form.get('example', '').strip()
        word.popularity = request.form.get('popularity', 0, type=int)
        word.synonyms = request.form.get('synonyms', '').strip()
        word.antonyms = request.form.get('antonyms', '').strip()
        word.usage_frequency = request.form.get('usage_frequency', 5, type=int)
        word.is_verified = request.form.get('is_verified') == 'on'
        tags_str = request.form.get('tags', '').strip()
        
        # Обновляем теги
        word.tags = []
        if tags_str:
            tag_names = [t.strip() for t in tags_str.split(',')]
            for tag_name in tag_names:
                if tag_name:
                    tag = Tag.query.filter_by(name=tag_name).first()
                    if not tag:
                        tag = Tag(name=tag_name)
                        db.session.add(tag)
                    word.tags.append(tag)
        
        try:
            # Создаём запись истории
            changes = []
            for field, old_value in old_values.items():
                new_value = getattr(word, field)
                if old_value != new_value:
                    changes.append(f'{field}: {old_value} → {new_value}')
            
            if changes:
                from models import WordHistory
                history = WordHistory(
                    word_id=word.id,
                    changed_by='Anonymous',  # В реальной реализации: current_user.username
                    changes=', '.join(changes)
                )
                db.session.add(history)
            
            db.session.commit()
            flash(f'Слово "{word.word}" успешно обновлено!', 'success')
            return redirect(url_for('word_detail', word_id=word.id))
        except Exception as e:
            db.session.rollback()
            flash(f'Ошибка при обновлении: {str(e)}', 'danger')
    
    periods = Period.query.all()
    categories = Category.query.all()
    return render_template('edit_word.html', word=word, periods=periods, categories=categories)

# Удаление слова
@app.route('/word/<int:word_id>/delete', methods=['POST'])
def delete_word(word_id):
    word = Word.query.get_or_404(word_id)
    try:
        db.session.delete(word)
        db.session.commit()
        flash(f'Слово "{word.word}" успешно удалено!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка при удалении: {str(e)}', 'danger')
    
    return redirect(url_for('index'))

# Статистика
@app.route('/statistics')
def statistics():
    total_words = Word.query.count()
    total_periods = Period.query.count()
    total_categories = Category.query.count()
    
    # Конвертируем результаты запросов в словари для JSON сериализации
    words_by_period_raw = db.session.query(
        Period.id,
        Period.name,
        Period.decade,
        db.func.count(Word.id).label('count')
    ).outerjoin(Word).group_by(Period.id).order_by(Period.start_year).all()
    
    words_by_period = [
        {'id': p.id, 'name': p.name, 'decade': p.decade, 'count': p.count}
        for p in words_by_period_raw
    ]
    
    words_by_category_raw = db.session.query(
        Category.id,
        Category.name,
        db.func.count(Word.id).label('count')
    ).outerjoin(Word).group_by(Category.id).order_by(desc('count')).all()
    
    words_by_category = [
        {'id': c.id, 'name': c.name, 'count': c.count}
        for c in words_by_category_raw
    ]
    
    # Получаем теги с количеством слов для облака тегов
    tags_raw = db.session.query(
        Tag.id,
        Tag.name,
        Tag.color,
        db.func.count(word_tags.c.word_id).label('count')
    ).outerjoin(word_tags).group_by(Tag.id).order_by(desc('count')).all()
    
    tags = [{'id': t.id, 'name': t.name, 'color': t.color, 'count': t.count} for t in tags_raw]
    
    popular_words = Word.query.order_by(desc(Word.popularity)).limit(10).all()
    recent_words = Word.query.order_by(desc(Word.created_at)).limit(5).all()
    
    return render_template('statistics.html',
                         total_words=total_words,
                         total_periods=total_periods,
                         total_categories=total_categories,
                         words_by_period=words_by_period,
                         words_by_category=words_by_category,
                         tags=tags,
                         popular_words=popular_words,
                         recent_words=recent_words)

# API для получения статистики в JSON
@app.route('/api/statistics')
def api_statistics():
    stats = {
        'total_words': Word.query.count(),
        'total_periods': Period.query.count(),
        'total_categories': Category.query.count(),
        'words_by_period': [
            {'period': p.name, 'decade': p.decade, 'count': p.count}
            for p in db.session.query(
                Period.name, Period.decade,
                db.func.count(Word.id).label('count')
            ).outerjoin(Word).group_by(Period.id).all()
        ],
        'words_by_category': [
            {'category': c.name, 'count': c.count}
            for c in db.session.query(
                Category.name,
                db.func.count(Word.id).label('count')
            ).outerjoin(Word).group_by(Category.id).all()
        ]
    }
    return jsonify(stats)

# API для поиска слов
@app.route('/api/search')
def api_search():
    query = request.args.get('q', '')
    tag_name = request.args.get('tag', '')
    period_id = request.args.get('period', type=int)
    category_id = request.args.get('category', type=int)
    
    words_query = Word.query.filter(Word.is_archived == False)
    
    if query:
        words_query = words_query.filter(
            or_(
                Word.word.ilike(f'%{query}%'),
                Word.meaning.ilike(f'%{query}%'),
                Word.synonyms.ilike(f'%{query}%')
            )
        )
        
    if tag_name:
        tag = Tag.query.filter_by(name=tag_name).first()
        if tag:
            words_query = words_query.filter(Word.tags.contains(tag))
    
    if period_id:
        words_query = words_query.filter(Word.period_id == period_id)
    
    if category_id:
        words_query = words_query.filter(Word.category_id == category_id)
    
    words = words_query.order_by(desc(Word.popularity)).limit(20).all()
    
    result = [{
        'id': w.id,
        'word': w.word,
        'meaning': w.meaning,
        'period': w.period.name if w.period else None,
        'category': w.category.name if w.category else None,
        'tags': [t.name for t in w.tags],
        'score': w.get_vote_score()
    } for w in words]
    
    return jsonify(result)


# ==================== НОВЫЕ API ====================

# API: Временная шкала сленга по периодам
@app.route('/api/timeline')
def api_timeline():
    """Возвращает количество слов по периодам для графика."""
    timeline_data = db.session.query(
        Period.name,
        Period.decade,
        Period.start_year,
        Period.color,
        func.count(Word.id).label('count')
    ).outerjoin(Word).group_by(Period.id).order_by(Period.start_year).all()
    
    return jsonify([{
        'period': p.name,
        'decade': p.decade,
        'start_year': p.start_year,
        'color': p.color,
        'count': p.count
    } for p in timeline_data])


# API: Популярные теги
@app.route('/api/popular-tags')
def api_popular_tags():
    """Возвращает самые популярные теги."""
    tag_counts = db.session.query(
        Tag.name,
        Tag.color,
        func.count(word_tags.c.word_id).label('count')
    ).join(word_tags).group_by(Tag.id).order_by(desc('count')).limit(15).all()
    
    return jsonify([{
        'name': t.name,
        'color': t.color,
        'count': t.count
    } for t in tag_counts])


# API: Детальная статистика
@app.route('/api/detailed-stats')
def api_detailed_stats():
    """Возвращает подробную статистику для визуализации."""
    # Слова по периодам (для круговой диаграммы)
    by_period = db.session.query(
        Period.name,
        func.count(Word.id).label('count')
    ).join(Word).group_by(Period.id).all()
    
    # Слова по категориям
    by_category = db.session.query(
        Category.name,
        func.count(Word.id).label('count')
    ).join(Word).group_by(Category.id).all()
    
    # Топ слов по популярности
    top_words = Word.query.filter(Word.is_archived == False).order_by(
        desc(Word.popularity)
    ).limit(10).all()
    
    # Активность по времени (слова по месяцам за последний год)
    one_year_ago = datetime.utcnow().replace(year=datetime.utcnow().year - 1)
    activity = db.session.query(
        func.strftime('%Y-%m', Word.created_at).label('month'),
        func.count(Word.id).label('count')
    ).filter(Word.created_at >= one_year_ago).group_by('month').all()
    
    return jsonify({
        'by_period': [{'name': p.name, 'count': p.count} for p in by_period],
        'by_category': [{'name': c.name, 'count': c.count} for c in by_category],
        'top_words': [{'word': w.word, 'popularity': w.popularity} for w in top_words],
        'activity': [{'month': a.month, 'count': a.count} for a in activity]
    })


# API: Эволюция слова по периодам
@app.route('/api/word/<int:word_id>/evolution')
def api_word_evolution(word_id):
    """Возвращает данные для таймлайна эволюции слова."""
    word = Word.query.get_or_404(word_id)
    
    # Находим слова с таким же значением/синонимами в других периодах
    similar_words = Word.query.filter(
        db.or_(
            Word.word.ilike(f'%{word.word}%'),
            Word.synonyms.ilike(f'%{word.word}%'),
            Word.meaning.ilike(f'%{word.meaning[:30]}%')
        ),
        Word.id != word.id
    ).order_by(Word.period_id).all()
    
    evolution_data = [{
        'id': w.id,
        'word': w.word,
        'period': w.period.name if w.period else 'N/A',
        'decade': w.period.decade if w.period else 'N/A',
        'start_year': w.period.start_year if w.period else 0,
        'meaning': w.meaning[:100],
        'is_current': w.id == word.id
    } for w in [word] + similar_words[:5]]
    
    # Сортируем по времени
    evolution_data.sort(key=lambda x: x['start_year'])
    
    return jsonify(evolution_data)


# API: Похожие слова (рекомендации)
@app.route('/api/word/<int:word_id>/similar')
def api_similar_words(word_id):
    """Возвращает похожие слова для рекомендаций."""
    word = Word.query.get_or_404(word_id)
    
    # Критерии похожести:
    # 1. Тот же период
    # 2. Та же категория
    # 3. Общие теги
    
    similar_query = Word.query.filter(
        Word.id != word.id,
        Word.is_archived == False
    )
    
    # Если есть теги, добавляем слова с общими тегами
    if word.tags:
        tag_ids = [t.id for t in word.tags]
        similar_query = similar_query.filter(Word.tags.any(Tag.id.in_(tag_ids)))
    elif word.period_id:
        # Если нет тегов, берём слова из того же периода
        similar_query = similar_query.filter_by(period_id=word.period_id)
    elif word.category_id:
        # Или из той же категории
        similar_query = similar_query.filter_by(category_id=word.category_id)
    
    # Сортируем по популярности
    similar_words = similar_query.order_by(desc(Word.popularity)).limit(6).all()
    
    result = [{
        'id': w.id,
        'word': w.word,
        'meaning': w.meaning[:80],
        'period': w.period.decade if w.period else 'N/A',
        'popularity': w.popularity
    } for w in similar_words]
    
    return jsonify(result)


# Топ слов по периоду
@app.route('/period/<int:period_id>/top')
def period_top_words(period_id):
    """Популярные слова определённого периода."""
    period = Period.query.get_or_404(period_id)
    words = Word.query.filter_by(period_id=period_id).order_by(desc(Word.popularity)).limit(20).all()
    periods = Period.query.all()
    return render_template('period_top.html', period=period, words=words, periods=periods)


# ==================== ЭКСПОРТ ДАННЫХ ====================

@app.route('/export/csv')
def export_csv():
    """Экспорт всех слов в CSV формат."""
    words = Word.query.filter(Word.is_archived == False).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    
    # Заголовки
    writer.writerow([
        'ID', 'Слово', 'Значение', 'Период', 'Категория',
        'Происхождение', 'Пример', 'Синонимы', 'Антонимы',
        'Популярность', 'Частота использования', 'Теги'
    ])
    
    for word in words:
        writer.writerow([
            word.id,
            word.word,
            word.meaning,
            word.period.name if word.period else '',
            word.category.name if word.category else '',
            word.origin or '',
            word.example or '',
            word.synonyms or '',
            word.antonyms or '',
            word.popularity,
            word.usage_frequency,
            ', '.join([t.name for t in word.tags])
        ])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode('utf-8-sig')),
        mimetype='text/csv',
        as_attachment=True,
        download_name=f'slang_export_{datetime.now().strftime("%Y%m%d")}.csv'
    )


@app.route('/export/json')
def export_json():
    """Экспорт всех слов в JSON формат."""
    words = Word.query.filter(Word.is_archived == False).all()
    
    data = []
    for word in words:
        data.append({
            'id': word.id,
            'word': word.word,
            'meaning': word.meaning,
            'period': word.period.name if word.period else None,
            'category': word.category.name if word.category else None,
            'origin': word.origin,
            'example': word.example,
            'synonyms': word.get_synonyms_list(),
            'antonyms': word.get_antonyms_list(),
            'popularity': word.popularity,
            'usage_frequency': word.usage_frequency,
            'is_verified': word.is_verified,
            'tags': [t.name for t in word.tags],
            'sources': [{
                'type': s.source_type,
                'title': s.title,
                'author': s.author,
                'year': s.year,
                'url': s.url
            } for s in word.sources],
            'created_at': word.created_at.isoformat()
        })
    
    return jsonify(data)


# ==================== УПРАВЛЕНИЕ ТЕГАМИ ====================

@app.route('/tags')
def tags_list():
    """Страница со списком всех тегов."""
    tags = Tag.query.order_by(Tag.name).all()
    return render_template('tags.html', tags=tags)


@app.route('/tag/<tag_name>')
def tag_words(tag_name):
    """Страница со словами определённого тега."""
    tag = Tag.query.filter_by(name=tag_name).first_or_404()
    words = Word.query.filter(Word.tags.contains(tag)).all()
    return render_template('tag_words.html', tag=tag, words=words)


# ==================== ГОЛОСОВАНИЕ ====================

@app.route('/api/vote', methods=['POST'])
def vote_word():
    """Голосование за слово (localStorage + БД для статистики)."""
    data = request.get_json()
    word_id = data.get('word_id')
    vote_type = data.get('vote_type')  # 1 или -1
    
    if vote_type not in [1, -1]:
        return jsonify({'error': 'Invalid vote type'}), 400
    
    word = Word.query.get(word_id)
    if not word:
        return jsonify({'error': 'Word not found'}), 404
    
    # Увеличиваем счётчик популярности напрямую
    if vote_type == 1:
        word.popularity += 1
    else:
        word.popularity = max(0, word.popularity - 1)
    
    db.session.commit()
    
    return jsonify({
        'success': True,
        'new_popularity': word.popularity,
        'vote_type': vote_type
    })


# Страница избранного
@app.route('/favorites')
def favorites():
    """Страница избранных слов (localStorage)."""
    # Получаем IDs избранных слов из query параметра
    favorite_ids = request.args.get('ids', '')
    if favorite_ids:
        ids = [int(x) for x in favorite_ids.split(',') if x.strip()]
        words = Word.query.filter(Word.id.in_(ids)).all()
    else:
        words = []
    
    return render_template('favorites.html', words=words)


# ==================== ИЗБРАННОЕ ====================

@app.route('/api/favorite/<int:word_id>', methods=['POST'])
def toggle_favorite_api(word_id):
    """API для добавления/удаления из избранного (localStorage)."""
    return jsonify({'success': True, 'word_id': word_id})


# ==================== КОММЕНТАРИИ ====================

@app.route('/word/<int:word_id>/comment', methods=['POST'])
def add_comment(word_id):
    """Добавить анонимный комментарий к слову."""
    word = Word.query.get_or_404(word_id)
    content = request.form.get('content', '').strip()
    author = request.form.get('author', '').strip()
    
    if not content:
        flash('Комментарий не может быть пустым', 'danger')
        return redirect(url_for('word_detail', word_id=word_id))
    
    if len(content) > 1000:
        flash('Комментарий слишком длинный (макс. 1000 символов)', 'danger')
        return redirect(url_for('word_detail', word_id=word_id))
    
    # Сохраняем имя автора в session для удобства
    if author:
        from flask import session
        session['comment_author'] = author
    
    try:
        # Создаём анонимный комментарий
        comment = Comment(
            word_id=word_id,
            user_id=None,  # Анонимно
            content=content[:1000],
            created_at=datetime.utcnow()
        )
        
        # Сохраняем имя автора в content
        if author:
            comment.content = f"**{author}**: {content}"
        
        db.session.add(comment)
        db.session.commit()
        
        flash('Комментарий добавлен!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ошибка: {str(e)}', 'danger')
    
    return redirect(url_for('word_detail', word_id=word_id))


@app.route('/api/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(comment_id):
    """Удалить комментарий (только для админа)."""
    comment = Comment.query.get_or_404(comment_id)
    
    try:
        db.session.delete(comment)
        db.session.commit()
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)