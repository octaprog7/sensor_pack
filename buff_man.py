from micropython import const

class BufferManager:
    """
    Менеджер буфера(ов) в ОЗУ для эффективной работы с периферией в MicroPython.
    """
    # размер буфера по умолчанию
    DEF_SIZE = const(32)

    def __init__(self, max_size: int = DEF_SIZE, sync: bool = False):
        """
        Инициализирует менеджер буферов в ОЗУ.

        Выделяет единый блок памяти (bytearray) заданного размера для последующего
        эффективного распределения буферов без копирования данных на основе memoryview.

        Args:
            max_size (int): Общий размер буфера в байтах.
                - Минимум: 1 байт
                - Рекомендуется: 32-256 байт для датчиков Sensirion
                - Максимум: ограничен доступной ОЗУ микроконтроллера
                По умолчанию: 32 байт…e)
            >>> buf = buf_mgr.get(16)
            >>> # ... использование ...
            >>> # reset() не требуется

            >>> # Режим выделения памяти для TX+RX транзакций
            >>> buf_mgr = BufferManager(max_size=64, sync=False)
            >>> tx_buf = buf_mgr.get(8)
            >>> rx_buf = buf_mgr.get(8)  # Не пересекается(!) с tx_buf
            >>> # ... использование ...
            >>> buf_mgr.reset()  # Сброс для следующей транзакции
        """
        self._buffer = bytearray(max_size)  # выделил буфер
        self._view = memoryview(self._buffer)
        self._size = max_size
        self._sync = sync
        self._offset = 0
        # Статистика
        self._stat_min = max_size
        self._stat_max = 0

    def get(self, length: int) -> memoryview:
        """
        Получить временный доступ к буферу заданной длины.

        Возвращает memoryview на часть внутреннего буфера без копирования данных.
        В режиме sync=True буфер переиспользуется от начала.
        В режиме sync=False выделения идут последовательно до reset().

        Args:
            length (int): Длина буфера в байтах (1..max_size).

        Returns:
            memoryview: Представление буфера для работы с периферией.

        Raises:
            ValueError: Если length <= 0 или превышает размер буфера.
            MemoryError: В режиме allocator, если недостаточно места.
        """
        len_of_buf = self._size

        # проверка
        if not 1 <= length <= len_of_buf:
            raise ValueError(f"Запрошенный размер {length} должен быть в диапазоне [1, {len_of_buf}]")

        # Подготовка смещения
        if self._sync:
            self._offset = 0
        elif self._offset + length > len_of_buf:
            raise MemoryError("Недостаточно места в буфере")

        # Создание среза
        view = self._view[self._offset : self._offset + length]

        # Обновление смещения
        if not self._sync:
            self._offset += length

        # Обновление статистики
        if length > self._stat_max:
            self._stat_max = length
        if length < self._stat_min:
            self._stat_min = length
        #
        return view

    def reset(self) -> None:
        """Сбросить счётчик выделителя (в режиме sync==True не требуется)"""
        self._offset = 0

    def get_stats(self) -> tuple[int, int]:
        """
        Получить статистику размеров запрошенных буферов.
        Возвращает кортеж (min_size, max_size).
        """
        return self._stat_min, self._stat_max