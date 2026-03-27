# Geometry Engine Documentation

## Обзор

Модуль `geometry.py` предоставляет движок для вычисления пересечений между примитивами и системы привязки (snapping) к характерным точкам объектов.

## Основные возможности

### 1. Пересечение примитивов

Поддерживается вычисление точек пересечения между:
- **Line-Line**: Два отрезка прямой
- **Line-Circle**: Отрезок и окружность
- **Line-Rectangle**: Отрезок и прямоугольник
- **Circle-Circle**: Две окружности
- **Circle-Rectangle**: Окружность и прямоугольник
- **Rectangle-Rectangle**: Два прямоугольника (пересечение кромок)

### 2. Точки привязки (Snapping Points)

Для каждого типа примитива определены характерные точки, к которым может происходить привязка:

#### Line (Отрезок)
- Начальная точка (start)
- Конечная точка (end)
- Средняя точка (midpoint)

#### Circle (Окружность) ⭐
- **Центр окружности** (center) - ключевая точка для кругов
- 4 кардинальные точки (N, S, E, W) на пересечении с осями

#### Rectangle (Прямоугольник)
- 4 угла (corners)
- Центр (center)
- 4 середины сторон (edge midpoints)

### 3. Привязка к точкам пересечения

Система автоматически вычисляет точки пересечения между всеми парами объектов и предлагает их как точки привязки.

## Использование

### Пример 1: Поиск пересечений

```python
from drawing_editor.core.models import LineObject, CircleObject
from drawing_editor.core.geometry import GeometryEngine

# Создать объекты
line = LineObject(0, 0, 10, 10)
circle = CircleObject(5, 5, 3)

# Найти все точки пересечения
results = GeometryEngine.find_intersections(line, circle)

for result in results:
    print(f"Пересечение в точке: ({result.point.x}, {result.point.y})")
    print(f"Между объектами: {type(result.shape_a).__name__} и {type(result.shape_b).__name__}")
```

### Пример 2: Привязка курсора

```python
from drawing_editor.core.models import LineObject, CircleObject
from drawing_editor.core.geometry import GeometryEngine

# Список всех объектов на сцене
shapes = [
    LineObject(0, 0, 10, 10),
    CircleObject(5, 5, 3),
]

# Позиция курсора мыши
cursor_x, cursor_y = 5.2, 4.8

# Найти ближайшую точку привязки
snap_point = GeometryEngine.find_snap_point(
    cursor_x, 
    cursor_y, 
    shapes,
    exclude_shape=None  # Или указать объект, который нужно игнорировать
)

if snap_point:
    print(f"Привязка к точке: ({snap_point.x}, {snap_point.y})")
else:
    print("Нет точек привязки в пределах порога")
```

### Пример 3: Получение всех точек привязки объекта

```python
from drawing_editor.core.models import CircleObject
from drawing_editor.core.geometry import GeometryEngine

circle = CircleObject(10, 10, 5)

# Получить все характерные точки круга
points = GeometryEngine.get_snapping_points(circle)

print(f"Точки привязки для круга:")
for i, pt in enumerate(points):
    print(f"  {i}: ({pt.x}, {pt.y})")
# Вывод:
#   0: (10.0, 10.0)      <- Центр
#   1: (10.0, 5.0)       <- Север
#   2: (10.0, 15.0)      <- Юг
#   3: (15.0, 10.0)      <- Восток
#   4: (5.0, 10.0)       <- Запад
```

## API Reference

### Класс `GeometryEngine`

#### Методы для вычисления пересечений

| Метод | Описание |
|-------|----------|
| `line_line_intersection(l1, l2)` | Пересечение двух отрезков |
| `line_circle_intersection(line, circle)` | Пересечение отрезка и окружности |
| `line_rect_intersection(line, rect)` | Пересечение отрезка и прямоугольника |
| `circle_circle_intersection(c1, c2)` | Пересечение двух окружностей |
| `find_intersections(shape_a, shape_b)` | Универсальный метод для любых пар |

#### Методы для привязки

| Метод | Описание |
|-------|----------|
| `get_snapping_points(shape)` | Вернуть список характерных точек объекта |
| `find_snap_point(x, y, shapes, exclude_shape)` | Найти ближайшую точку привязки |

### Класс `GeometryPoint`

Простая структура для хранения координат:

```python
class GeometryPoint:
    x: float  # X координата
    y: float  # Y координата
```

### Класс `IntersectionResult`

Результат пересечения двух объектов:

```python
class IntersectionResult:
    point: GeometryPoint     # Точка пересечения
    shape_a: GraphicObject   # Первый объект
    shape_b: GraphicObject   # Второй объект
```

## Константы

```python
GeometryEngine.EPSILON = 1e-6        # Точность для float сравнений
GeometryEngine.SNAP_THRESHOLD = 10.0 # Порог привязки в пикселях
```

## Интеграция с Trim командой

Для реализации команды Trim (Обрезка):

1. **Выберите режущие объекты** (cutting objects)
2. **Выберите объекты для обрезки** (objects to trim)
3. **Укажите точку клика** на части, которую нужно удалить
4. **Используйте `find_intersections()`** для нахождения точек пересечения
5. **Разделите объект** по точкам пересечения
6. **Определите сегмент** для удаления по точке клика
7. **Создайте команду** через Command Pattern для поддержки Undo/Redo

```python
# Псевдокод для Trim
def trim_object(object_to_trim, cutting_objects, click_point):
    # 1. Найти все точки пересечения
    all_intersections = []
    for cutter in cutting_objects:
        intersections = GeometryEngine.find_intersections(object_to_trim, cutter)
        all_intersections.extend(intersections)
    
    # 2. Сортировать точки вдоль объекта
    # 3. Разделить объект на сегменты
    # 4. Найти сегмент, содержащий click_point
    # 5. Удалить этот сегмент
    pass
```

## Тестирование

Все функции покрыты юнит-тестами в `tests/test_geometry.py`:

```bash
python -m unittest tests.test_geometry -v
```

18 тестов проверяют:
- ✅ Пересечение line-line
- ✅ Пересечение line-circle (включая касательные)
- ✅ Пересечение circle-circle
- ✅ Пересечение line-rect
- ✅ Пересечение circle-rect
- ✅ Точки привязки для всех примитивов
- ✅ Привязка к центру окружности
- ✅ Исключение объектов из привязки
