def close(self):
    """Закрытие соединения с базой данных"""
    try:
        if hasattr(self, 'connection') and self.connection is not None:
            self.connection.close()
            self.connection = None
            logger.info("Соединение с базой данных закрыто")
    except Exception as e:
        logger.error(f"Ошибка при закрытии соединения с базой данных: {e}") 