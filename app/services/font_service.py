# app/services/font_service.py
import os
import logging
from typing import List, Dict, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class FontService:
    """字体提取服务类"""

    # 常量定义
    HZK_DIMENSIONS = {
        12: (16, 12),  # HZK12: 宽度16, 高度12
    }
    HZK_FILES = {
        12: "HZK12"
    }
    ASC_FILES = {
        12: "ASC12"
    }

    def __init__(self):
        self.hzk_data: Optional[bytes] = None
        self.asc_data: Optional[bytes] = None
        self.current_font_type: Optional[str] = None
        self.current_font_size: Optional[int] = None
        self.font_width: int = 0
        self.font_height: int = 0
        # 字体文件路径
        base_dir = os.path.dirname(os.path.dirname(__file__))
        self.hzk_path = os.path.join(base_dir, "assets", "HZK")
        self.asc_path = os.path.join(base_dir, "assets", "ASC")

    def load_font(self, font_type: str, font_size: int) -> bool:
        """加载指定类型和尺寸的字库"""
        self.current_font_type = font_type
        self.current_font_size = font_size

        try:
            if font_type == "HZK":
                self._load_hzk_font(font_size)
            elif font_type == "ASC":
                self._load_asc_font(font_size)
            else:
                raise ValueError(f"不支持的字体类型: {font_type}")
            return True
        except Exception as e:
            logger.error(f"加载字体失败: {e}")
            return False

    def _load_hzk_font(self, font_size: int) -> None:
        """加载HZK字库"""
        if font_size not in self.HZK_DIMENSIONS:
            raise ValueError(f"不支持的HZK字体大小: {font_size}")

        self.font_width, self.font_height = self.HZK_DIMENSIONS[font_size]
        file_path = os.path.join(self.hzk_path, self.HZK_FILES[font_size])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"HZK字库文件不存在: {file_path}")

        with open(file_path, 'rb') as f:
            self.hzk_data = f.read()

    def _load_asc_font(self, font_size: int) -> None:
        """加载ASC字库"""
        if font_size not in self.ASC_FILES:
            raise ValueError(f"不支持的ASC字体大小: {font_size}")

        self.font_width = 8  # ASC字库宽度固定为8
        self.font_height = font_size
        file_path = os.path.join(self.asc_path, self.ASC_FILES[font_size])
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"ASC字库文件不存在: {file_path}")

        with open(file_path, 'rb') as f:
            self.asc_data = f.read()

    def get_char_bytes_count(self) -> int:
        """获取每个字符占用的字节数"""
        if self.current_font_type == "HZK":
            return (self.font_width * self.font_height) // 8
        elif self.current_font_type == "ASC":
            return self.font_height
        else:
            raise ValueError("未加载字体类型")

    def get_hzk_char_offset(self, char: str) -> int:
        """获取汉字在HZK字库中的偏移量"""
        if not self.hzk_data:
            raise ValueError("HZK字库未加载")

        gb_bytes = char.encode('gb2312')
        if len(gb_bytes) != 2:
            raise ValueError(f"不支持的字符编码: {char}")

        high_byte, low_byte = gb_bytes[0], gb_bytes[1]
        if high_byte < 0xA1 or low_byte < 0xA1:
            raise ValueError(f"字符不在GB2312编码范围内: {char}")

        zone_code = high_byte - 0xA0
        pos_code = low_byte - 0xA0
        bytes_per_char = self.get_char_bytes_count()
        offset = ((zone_code - 1) * 94 + (pos_code - 1)) * bytes_per_char

        if offset + bytes_per_char > len(self.hzk_data):
            raise ValueError(f"字符偏移量超出字库范围: {char}")

        return offset

    def get_asc_char_offset(self, char: str) -> int:
        """获取ASCII字符在ASC字库中的偏移量"""
        if not self.asc_data:
            raise ValueError("ASC字库未加载")

        ascii_code = ord(char)
        if ascii_code < 32 or ascii_code > 126:
            raise ValueError(f"ASCII字符必须在32-126范围内: {char}")

        bytes_per_char = self.get_char_bytes_count()
        offset = (ascii_code - 32) * bytes_per_char

        if offset + bytes_per_char > len(self.asc_data):
            raise ValueError(f"字符偏移量超出字库范围: {char}")

        return offset

    def extract_char_matrix(self, char: str) -> List[List[int]]:
        """提取字符点阵数据"""
        if not self.current_font_type:
            raise ValueError("未加载字体类型")

        if self.current_font_type == "HZK":
            return self._extract_hzk_char_matrix(char)
        else:
            return self._extract_asc_char_matrix(char)

    def _extract_hzk_char_matrix(self, char: str) -> List[List[int]]:
        """提取HZK汉字点阵数据"""
        offset = self.get_hzk_char_offset(char)
        bytes_per_char = self.get_char_bytes_count()
        char_data = self.hzk_data[offset:offset + bytes_per_char]

        if self.current_font_size == 12:
            return self._extract_hzk12_char_matrix(char_data)
        else:
            return self._extract_hzk_common_char_matrix(char_data)

    def _extract_hzk12_char_matrix(self, char_data: bytes) -> List[List[int]]:
        """提取HZK12汉字点阵数据（16x12点阵）"""
        matrix = []
        for row in range(12):  # 12行
            row_data = []
            byte1 = char_data[row * 2]
            byte2 = char_data[row * 2 + 1]

            # 提取两个字节的16位数据
            for byte in (byte1, byte2):
                for i in range(8):
                    pixel = (byte >> (7 - i)) & 0x01
                    row_data.append(pixel)
            matrix.append(row_data)
        return matrix

    def _extract_hzk_common_char_matrix(self, char_data: bytes) -> List[List[int]]:
        """提取通用HZK汉字点阵数据"""
        if not isinstance(char_data, bytes):
            char_data = char_data.encode('latin1') if isinstance(char_data, str) else bytes(char_data)

        bytes_per_row = (self.font_width + 7) // 8
        matrix = []
        for row in range(self.font_height):
            row_data = []
            for byte_idx in range(bytes_per_row):
                byte_pos = row * bytes_per_row + byte_idx
                if byte_pos < len(char_data):
                    byte_val = char_data[byte_pos]
                    if isinstance(byte_val, str):
                        byte_val = ord(byte_val)
                    for bit in range(8):
                        if byte_idx * 8 + bit < self.font_width:
                            pixel = (byte_val >> (7 - bit)) & 0x01
                            row_data.append(pixel)
            matrix.append(row_data)
        return matrix

    def _extract_asc_char_matrix(self, char: str) -> List[List[int]]:
        """提取ASCII字符点阵数据"""
        offset = self.get_asc_char_offset(char)
        bytes_per_char = self.get_char_bytes_count()
        char_data = self.asc_data[offset:offset + bytes_per_char]

        matrix = []
        for row in range(self.font_height):
            byte = char_data[row]
            row_data = [(byte >> (7 - bit)) & 0x01 for bit in range(8)]
            matrix.append(row_data)
        return matrix

    def preview_char(self, char: str) -> List[str]:
        """生成字符预览文本"""
        matrix = self.extract_char_matrix(char)
        return ["".join("■" if pixel else "□" for pixel in row) for row in matrix]

    def get_supported_fonts(self) -> Dict:
        """获取支持的字体列表"""
        return {
            "HZK": list(self.HZK_DIMENSIONS.keys()),
            "ASC": list(self.ASC_FILES.keys())
        }

    def generate_c51_code(
            self,
            text: str,
            arrangement: str = "horizontal",
            mode: str = "vertical_upper",
            invert: bool = False,
            array_name: str = ""
    ) -> str:
        """生成C51格式的字体数组代码"""
        if not self.current_font_type:
            raise ValueError("未加载字体类型")

        # 生成数组名
        array_name = array_name or f"font_{self.current_font_type}{self.current_font_size}"

        # 处理每个字符的点阵数据
        hex_data = []
        for char in text:
            matrix = self.extract_char_matrix(char)

            # 根据排列方式处理矩阵
            if arrangement == "vertical":
                matrix = self._transpose_matrix(matrix)

            # 将点阵矩阵转换为字节数组
            byte_array = self._matrix_to_bytes(matrix, mode, invert)
            hex_data.extend(f"0x{b:02X}" for b in byte_array)

        # 生成C代码
        if not hex_data:
            raise ValueError("生成的C代码为空，请检查输入文本或字体数据")

        c_code = [
            f"unsigned char code {array_name}[] = {{",
            ",\n".join(", ".join(hex_data[i:i + 16]) for i in range(0, len(hex_data), 16)),
            "};"
        ]
        return "\n".join(c_code)

    def _transpose_matrix(self, matrix: List[List[int]]) -> List[List[int]]:
        """矩阵转置（用于垂直排列）"""
        return [list(col) for col in zip(*matrix)]

    def _matrix_to_bytes(
            self,
            matrix: List[List[int]],
            mode: str,
            invert: bool
    ) -> List[int]:
        """将点阵矩阵转换为字节数组"""
        bytes_list = []
        for row in matrix:
            byte = 0
            for i, pixel in enumerate(row):
                if invert:
                    pixel = 1 - pixel
                if mode == "vertical_upper":
                    byte |= (pixel << (7 - i % 8))
                elif mode == "vertical_lower":
                    byte |= (pixel << (i % 8))
                elif mode == "horizontal_upper":
                    byte |= (pixel << (7 - i))
                elif mode == "horizontal_lower":
                    byte |= (pixel << i)
            bytes_list.append(byte)
        return bytes_list
