import sys
import random
from PyQt5.QtWidgets import QApplication, QGraphicsScene, QGraphicsView, QGraphicsRectItem, QGraphicsLineItem, QGraphicsItem
from PyQt5.QtGui import QBrush, QColor, QPen, QPainter
from PyQt5.QtCore import Qt, QLineF, QRectF, QPointF


class DraggableRect(QGraphicsRectItem):
    def __init__(self, x, y, width, height, color):
        super().__init__(x, y, width, height)
        self.setBrush(QBrush(color))
        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.color = color
        self.setZValue(1)
        self.line_items = []
        self.initial_pos = QPointF()  # Инициализация пустой точки
        self.moving = False  # Флаг для предотвращения рекурсии

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionChange and not self.moving:
            self.moving = True  # Устанавливаем флаг, чтобы предотвратить повторный вызов
            new_pos = value  # Получаем новое положение относительно текущего
            rect = self.rect()  # Размер прямоугольника
            scene_rect = self.scene().sceneRect()  # Размеры сцены

            # Вычисляем потенциальное новое положение с учетом начальной позиции прямоугольника
            new_x = self.initial_pos.x() + new_pos.x()
            new_y = self.initial_pos.y() + new_pos.y()

            # Ограничиваем положение прямоугольника в пределах сцены
            corrected_x = min(max(scene_rect.left(), new_x), scene_rect.right() - rect.width())
            corrected_y = min(max(scene_rect.top(), new_y), scene_rect.bottom() - rect.height())

            # Возвращаем откорректированную позицию относительно текущего положения
            corrected_pos = QPointF(corrected_x - self.initial_pos.x(), corrected_y - self.initial_pos.y())

            # Проверяем коллизии с другими объектами на сцене
            temp_pos = self.pos()  # Сохраняем текущую позицию для отката в случае коллизии
            self.setPos(corrected_pos)  # Устанавливаем временно позицию для проверки коллизий
            for item in self.scene().items():
                if item is not self and isinstance(item, QGraphicsRectItem) and item.collidesWithItem(self):
                    self.setPos(temp_pos)  # Откатываем позицию, если есть коллизия
                    self.moving = False
                    return temp_pos

            self.update_lines()  # Обновление линий при изменении позиции прямоугольника
            self.moving = False
            return corrected_pos

        return super().itemChange(change, value)


    def find_nearest_free_position(self, corrected_pos, other_item):
        """Поиск ближайшей свободной позиции для перемещения при коллизии."""
        offset = 5  # Шаг сдвига при поиске свободной позиции
        directions = [(offset, 0), (-offset, 0), (0, offset), (0, -offset)]

        for dx, dy in directions:
            tentative_pos = QPointF(corrected_pos.x() + dx, corrected_pos.y() + dy)
            self.setPos(tentative_pos)
            if not self.collidesWithItem(other_item) and self.scene().sceneRect().contains(self.sceneBoundingRect()):
                return tentative_pos

        # Если нет доступных позиций, возвращаем исходную позицию
        return corrected_pos


    def update_lines(self):
        for line_item in self.line_items:
            line_item.update_line()

    def add_line(self, line_item):
        self.line_items.append(line_item)

    def remove_line(self, line_item):
        self.line_items.remove(line_item)


class DraggableLine(QGraphicsLineItem):
    def __init__(self, rect1, rect2):
        super().__init__()
        self.rect1 = rect1
        self.rect2 = rect2
        self.setPen(QPen(Qt.black, 2))
        self.update_line()
        self.setZValue(0)

    def update_line(self):
        rect1_center = self.rect1.sceneBoundingRect().center()
        rect2_center = self.rect2.sceneBoundingRect().center()
        self.setLine(QLineF(rect1_center, rect2_center))


class Scene(QGraphicsScene):
    def __init__(self):
        super().__init__()
        self.setSceneRect(0, 0, 800, 600)
        self.rects = []
        self.lines = []
        self.selected_rects = []

    def mouseDoubleClickEvent(self, event):
        pos = event.scenePos()
        rect_width = 100
        rect_height = 50
        rect_color = QColor(random.randint(0, 255), random.randint(0, 255), random.randint(0, 255))

        new_rect_x = pos.x() - rect_width / 2
        new_rect_y = pos.y() - rect_height / 2

        new_rect = QRectF(new_rect_x, new_rect_y, rect_width, rect_height)

        # Проверяем, что новый прямоугольник не выходит за границы сцены
        if not self.sceneRect().contains(new_rect):
            return

        # Проверяем, что новый прямоугольник не пересекается с другими прямоугольниками
        if any(rect.collidesWithItem(DraggableRect(new_rect.x(), new_rect.y(), rect_width, rect_height, rect_color)) for rect in self.rects):
            return

        rect = DraggableRect(new_rect.x(), new_rect.y(), rect_width, rect_height, rect_color)
        self.addItem(rect)
        rect.initial_pos = QPointF(new_rect_x, new_rect_y - rect_height / 2)  # Устанавливаем начальную позицию после добавления на сцену
        self.rects.append(rect)

    # Метод добавления/удаления связей (работает при Ctrl + click по двум прямоугольникам последовательно)
    def mousePressEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if event.modifiers() and Qt.ControlModifier and isinstance(item, DraggableRect):
            if item not in self.selected_rects:
                self.selected_rects.append(item)
                if len(self.selected_rects) == 2:
                    rect1, rect2 = self.selected_rects
                    line = self.find_line_between(rect1, rect2)
                    if line:
                        self.remove_line(line)
                    else:
                        self.add_line(rect1, rect2)
                    self.selected_rects.clear()
        else:
            self.selected_rects.clear()

        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.scenePos(), self.views()[0].transform())
        if isinstance(item, DraggableRect):
            self.resolve_collisions(item)
        super().mouseReleaseEvent(event)

    def resolve_collisions(self, rect):
        # Поправка для более точного разрешения коллизий
        moved = False
        while any(other_rect != rect and rect.collidesWithItem(other_rect) for other_rect in self.rects):
            for other_rect in self.rects:
                if other_rect != rect and rect.collidesWithItem(other_rect):
                    new_x = rect.x() + 10
                    new_y = rect.y() + 10

                    # Ограничиваем координаты так, чтобы прямоугольник не выходил за границы сцены
                    new_x = min(max(self.sceneRect().left(), new_x), self.sceneRect().right() - rect.rect().width())
                    new_y = min(max(self.sceneRect().top(), new_y), self.sceneRect().bottom() - rect.rect().height())

                    rect.setPos(new_x, new_y)
                    moved = True
                    break
            if not moved:
                break

    def find_line_between(self, rect1, rect2):
        for line in self.lines:
            if (line.rect1 == rect1 and line.rect2 == rect2) or (line.rect1 == rect2 and line.rect2 == rect1):
                return line
        return None

    def add_line(self, rect1, rect2):
        line = DraggableLine(rect1, rect2)
        self.addItem(line)
        rect1.add_line(line)
        rect2.add_line(line)
        self.lines.append(line)

    def remove_line(self, line):
        line.rect1.remove_line(line)
        line.rect2.remove_line(line)
        self.removeItem(line)
        self.lines.remove(line)


app = QApplication(sys.argv)
view = QGraphicsView()
scene = Scene()
view.setScene(scene)
view.setRenderHint(QPainter.Antialiasing)
view.show()
sys.exit(app.exec_())
