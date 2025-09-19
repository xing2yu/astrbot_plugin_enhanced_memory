def __init__(self, context: Context, config: Dict[str, Any]):
    super().__init__(context)  # 确保调用父类构造函数
    self.config = config
    # ... 其余的初始化代码