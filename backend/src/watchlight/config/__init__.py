# 文件说明：本文件属于 配置层。
# 主要职责：声明包边界和公共导出位置。
# 阅读提示：读取配置并处理环境变量替换。
# 运行影响：仅用于源码阅读，不改变运行逻辑。

"""Configuration loading, validation, and persistence."""

from watchlight.config.loader import load_config

__all__ = ["load_config"]
