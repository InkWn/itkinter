import tkinter as tk

__all__ = ["IkCanvas", "IkScrollBar"]


# 自定义画布，方便配合自定义滚轮
class IkCanvas(tk.Canvas):
    def __init__(
            self, master,
            expand_width: bool = True,
            expand_height: bool = True,
            show_width: int | float = ...,
            show_height: int | float = ...,
            camvas_width: int | float = 1000,
            canvas_height: int | float = 1000,
            wheel_step: int = 10,
            bg: str = None,
            bd: int = 0, highlightthickness: int = 0,
            *args, **kwargs
     ):
        """
        用grid,pack等布局时不要使用拓展参数，会出问题，若要拓展，应使用内部参数expand_width和expand_height；
        需绑定IkScroll时使用bind_scroll函数，仅支持IkScrollBar；
        要给IkCanvas绑定事件时，需要bind里添加参数add=True，否则会覆盖原有事件。
        :param master:   父容器
        :param expand_width:  宽度是否根据master扩展，最大不会超过canvas_width
        :param expand_height: 高度是否根据master扩展，最大不会超过canvas_height
        :param show_width:  绘制的宽度，expand_width为False时有效
        :param show_height: 绘制的高度，expand_height为False时有效
        :param camvas_width:    实际画布的宽度，需大于等于show_width
        :param canvas_height:   实际画布的高度，需大于等于show_height
        :param wheel_step: 滚轮每次滚动画布的大小
        :param bg:  背景色
        :param bd:  边框宽度
        :param highlightthickness: 边框宽度
        """
        super().__init__(master, *args, **kwargs)
        if wheel_step <= 0:  # 步长必须大于0
            raise ValueError("wheel_step must be greater than 0")
        # 是否扩展
        self.expand_width, self.expand_height = expand_width, expand_height
        master.update_idletasks()  # 刷新父容器尺寸
        if not self.expand_width:
            if show_width is ...:  # 宽度未指定
                raise ValueError("show_width must be specified when expand_width is False")
            else:
                if show_width > camvas_width:
                    raise ValueError("show_width > canvas_width")
        else:  # 扩展宽度
            show_width = master.winfo_width()
            if show_width > camvas_width:
                raise ValueError("master`s width > canvas_width")
        if not self.expand_height:
            if show_height is ...:  # 高度未指定
                raise ValueError("show_height must be specified when expand_height is False")
            else:
                if show_height > canvas_height:
                    raise ValueError("show_height > canvas_height")
        else:  # 扩展高度
            show_height = master.winfo_height()
            if show_height > canvas_height:
                raise ValueError("master`s height > canvas_height")
        # 画布参数
        if bg: self["bg"] = bg
        else: self["bg"] = master["bg"]
        self.config(width=show_width, height=show_height, bd=bd, highlightthickness=highlightthickness)
        # 参数
        self.canvas_width = camvas_width
        self.canvas_height = canvas_height
        self.wheel_step = wheel_step
        # 定位用的矩形
        self._locate = self.create_rectangle(0, 0, 0, 0, width=0)
        # 当前展示的比值
        self.ratio_x = 0.0
        self.ratio_y = 0.0
        # 底部坐标
        self.__right: int = 0  # 右部坐标
        self.__down: int = 0  # 底部坐标
        # 绑定事件
        self.bind("<Configure>", self.__on_resize)   # 绑定canvas大小改变事件
        if self.expand_width or self.expand_height:  # 绑定父容器大小改变事件
            self.__master_bind_configure_id = self.master.bind("<Configure>", self.__on_master_resize, add=True)
        self.bind("<MouseWheel>", self.__on_wheel)  # 绑定滚轮事件
        self.bind("<Destroy>", self.__on_destroy)  # 绑定销毁事件
        # 控件初始化
        self.y_scroll = None
        self.x_scroll = None
        self.update_idletasks()  # 刷新父容器尺寸

    # 绑定滚动条事件
    def bind_scroll(self, scrollbar: "IkScrollBar") -> bool:
        """
        如果抄代码没把IkScrollBar一起抄进来，IDE报错不用管，反正你不用IkScrollBar，bind_scroll函数也没啥用
        :param scrollbar:  仅支持IkScrollBar对象
        """
        if not isinstance(scrollbar, IkScrollBar):
            raise TypeError("scrollbar must be IkScrollBar object")
        if scrollbar.orient == "v": self.y_scroll = scrollbar
        else: self.x_scroll = scrollbar
        return True

    @property
    def get_ratio(self) -> tuple[float, float]:
        """
        获取当前展示的比值
        :return: (x比值, y比值)
        """
        return self.ratio_x, self.ratio_y

    @property
    def get_count(self) -> tuple[int, int]:
        """
        获取可移动距离
        :return: (右部可移动距离, 底部可移动距离)
        """
        return self.__right, self.__down

    @property
    def get_moved_count(self) -> tuple[int, int]:
        """
        获取已移动的距离
        :return: (x移动距离, y移动距离)
        """
        return abs(self.coords(self._locate)[0]), abs(self.coords(self._locate)[1])

    @property
    def get_leave_count(self) -> tuple[int, int]:
        """
        获取剩余可移动次数
        :return: (右部可移动次数, 底部可移动次数)
        """
        return (self.coords(self._locate)[0] + self.__right,
                self.coords(self._locate)[1] + self.__down)

    # 绑定canvas大小改变事件
    def __on_resize(self, event):
        self.__right = self.canvas_width - event.width  # 右部坐标
        self.__down = self.canvas_height - event.height  # 底部坐标
        if self.coords(self._locate)[0] + self.__right < 0:  # 右部超出范围
            self.move(-(self.coords(self._locate)[0] + self.__right), 0)  # 复位到右边，需要实时计算
        if self.coords(self._locate)[1] + self.__down < 0:  # 底部超出范围
            self.move(0, -(self.coords(self._locate)[1] + self.__down))  # 复位到底部

    # 父容器大小改变事件
    def __on_master_resize(self, event):
        width, height = self.master.winfo_width(), self.master.winfo_height()
        if self.expand_width:
            if width <= self.canvas_width:  # 现宽度未超过canvas_width
                self.config(width=width)
            else:
                if self.get_leave_count[0] < 0:  # 右部超出范围
                    self.move(self.coords(self._locate)[0], 0)  # 复位到右边
                self.config(width=self.canvas_width)
        if self.expand_height:
            if height <= self.canvas_height:  # 现高度未超过canvas_height
                self.config(height=height)
            else:
                if self.get_leave_count[1] < 0:  # 底部超出范围
                    self.move(0, self.coords(self._locate)[1])  # 复位到底部
                self.config(height=self.canvas_height)

    # 绑定滚轮事件
    def __on_wheel(self, event):
        wheel = self.wheel_step * event.delta / 120  # 滚动的大小
        if event.state & 1:  # 同时按下shift
            self.move(wheel, 0)  # 水平移动
        else:
            self.move(0, wheel)  # 垂直移动

    # 绑定销毁事件
    def __on_destroy(self, event):
        if self.expand_width or self.expand_height:
            self.master.unbind("<Configure>", self.__master_bind_configure_id)  # 解绑在本对象绑定的父容器大小改变事件
        self.unbind("<Configure>")
        self.unbind("<MouseWheel>")
        self.unbind("<Destroy>")

    # 计算比值
    def __calc(self) -> tuple[float, float]:
        _x, _y = 1.0, 1.0
        if self.__right != 0:
            _x = abs(self.coords(self._locate)[0] / self.__right)
            if _x >= 1: _x = 1.0
        if self.__down != 0:
            _y = abs(self.coords(self._locate)[1] / self.__down)
            if _y >= 1: _y = 1.0
        self.ratio_x, self.ratio_y = _x, _y
        return _x, _y

    # 移动
    def move(self,  x, y):
        if self.__right == 0 and x > 0: return  # 展示的画布与实际画布相等，不用移动
        if self.__down == 0 and y > 0: return  # 展示的画布与实际画布相等，不用移动
        locate = self.coords(self._locate)
        # 到顶了且向上移动
        if locate[1] >= 0 and y > 0:
            super().move("all", 0, -locate[1])
        # 到底了且向下移动
        elif locate[1] + y <= -self.__down and y < 0:
            super().move("all", 0, -(locate[1] + self.__down))
        # 到左边了且向左移动
        elif locate[0] >= 0 and x > 0:
            super().move("all", -locate[0], 0)
        # 到右边了且向右移动
        elif locate[0] + x <= -self.__right and x < 0:
            super().move("all", -(locate[0] + self.__right), 0)
        # 正常移动
        else: super().move("all", x, y)
        self.__calc()
        if self.y_scroll:  # 已绑定y滚动条
            try:
                if self.y_scroll.canvas is self:  # 已绑定本画布
                    self.y_scroll.move_slider(0, -self.coords(self._locate)[1])  # 移动滑块
            except AttributeError:  # 没有.canvas属性，说明还没绑定画布
                raise ValueError("y_scroll 未绑定本画布")
        if self.x_scroll:
            try:
                if self.x_scroll.canvas is self:  # 已绑定本画布
                    self.x_scroll.move_slider(-self.coords(self._locate)[0], 0)  # 移动滑块
            except AttributeError:  # 没有.canvas属性，说明还没绑定画布
                raise ValueError("x_scroll 未绑定本画布")

    # 移动到指定位置
    def move_to(self, direction: str):
        """
        移动到指定方向
        :param direction: 方向，up, down, left, right
        """
        locate = self.coords(self._locate)
        if direction == "up":
            self.move(0, -locate[1])
        elif direction == "down":
            self.move(0, -locate[1] + self.__down)
        elif direction == "left":
            self.move(-locate[0], 0)
        elif direction == "right":
            self.move(-locate[0] + self.__right, 0)
        else:
            raise ValueError("direction must be 'up', 'down', 'left', 'right'")
        self.__calc()


# 自定义滚动条
class IkScrollBar(tk.Canvas):
    def __init__(
            self,
            master: tk.Tk | tk.Canvas | tk.Frame,
            canvas: "IkCanvas" = ...,
            orient: str = "vertical",
            step: int | float = 1,
            wheel_step: int | float = 10,
            expand: bool = True,
            scroll_shorten: tuple[str, int | float] = (..., 0),
            scroll_width: int = 15, scroll_height: int = 15,
            scroll_bg: str | None = None,
            slider_width: int = 15, slider_height: int = 15,
            slider_min: int = 50,
            slider_side: str = "center",
            slider_bg: str = "#CDCDCD", focus_color: str = "#A6A6A6", press_color: str = "#606060",
            commands: dict[str, callable] = {"enter": None, "press": None, "release": None}
    ):
        """
        IkCanvas无需config(scrollregion=...)，就可直接使用IkScrollBar；
        以下参数的vertical（垂直）简写为v，horizontal（水平）简写为h。
        :param master: 父容器
        :param canvas: 绑定的画布，必须是IkCanvas，且不能与master相同，可后续绑定
        :param orient: 滚动条方向，可选参数(vertical, horizontal, v, h)
        :param step:  滑块每次滑动的步长，会影响scroll_width或scroll_height
        :param wheel_step: 滚轮滚动的步长
        :param expand:  是否自动扩展滚动条，默认True，orient为v时扩展高度，为h时扩展宽度
        :param scroll_shorten:  滚动条缩短量，参数：(方向，大小)，expand为True时有效，用于增加滚动条与窗口之间的距离，
            orient为v时参数1可选(up或down)，为h时参数1可选(left或right)，这个参数主要是为了防止滚动条被其他控件遮挡
        :param scroll_width:  滚动条宽度，expand为True时则跟随master的宽度，否则为指定值，必须大于slider_min
        :param scroll_height: 滚动条高度，expand为True时则跟随master的高度，否则为指定值，必须大于slider_min
        :param scroll_bg:   滚动条背景色, None则跟随父容器背景色
        :param slider_width:  滑块宽度，orient为vertical时有效
        :param slider_height: 滑块高度，orient为horizontal时有效
        :param slider_min:    滑块最小长度，小于此长度后step由内部控制，最小值不能小于5
        :param slider_side:   滑块位置，orient为v时可选参数(left、right、center)，为h时(top、bottom、center)
        :param slider_bg:    滑块无事件时的背景色
        :param focus_color:  鼠标悬停在滑块上时的颜色
        :param press_color:  鼠标按下滑块时的颜色
        :param commands: 滑块回调函数，键("enter", "press", "release")分别表示鼠标进入滚动条，鼠标按下，释放滑块，值为对应键的回调函数
        """
        super().__init__(master)
        # 参数检测
        if canvas is master:  # 父容器不能与画布相同
            raise ValueError("master cannot be the same as canvas")
        if step <= 0:  # 步长必须大于0
            raise ValueError("step must be greater than 0")
        if slider_min < 5:  # 滑块最小长度必须大于5
            raise ValueError("slider_min must be greater than 5")
        # 检查方向并简化参数
        if orient in ["v", "vertical"]:
            self.orient = "v"
        elif orient in ["h", "horizontal"]:
            self.orient = "h"
        else:
            raise ValueError("orient must be'vertical', 'horizontal', 'v' or 'h'")  # 方向错误
        # 参数检测
        if self.orient == "v":
            if scroll_shorten[0] is ...:
                scroll_shorten = ("up", 0)  # 默认向上缩短0
            elif scroll_shorten[0] not in ["up", "down"]:
                raise ValueError("orient为vertical时，scroll_shorten第一个参数只能为：up或down")
            if slider_side not in ["left", "right", "center"]:
                raise ValueError("orient为vertical时，slider_side只能为：left、right、center")
        else:
            if scroll_shorten[0] is ...:
                scroll_shorten = ("left", 0)  # 默认向左缩短0
            elif scroll_shorten[0] not in ["left", "right"]:
                raise ValueError("orient为horizontal时，scroll_shorten第一个参数只能为：left或right")
            if slider_side not in ["top", "bottom", "center"]:
                raise ValueError("orient为horizontal时，slider_side只能为：top、bottom、center")
        # 画布参数
        self.canvas = None  # 默认参数
        if canvas is not ...:
            if not isinstance(canvas, IkCanvas):  # 绑定的画布必须是IkCanvas
                raise TypeError("canvas must be an instance of IkCanvas")
            self.bind_canvas(canvas)  # 绑定画布
        # 滚动条参数
        master.update_idletasks()  # 刷新父容器尺寸
        if self.orient == "v":
            if expand:
                scroll_height = master.winfo_reqheight()  # 滚动条高度为父容器高度
            else:
                if scroll_height <= slider_min:  # 高度小于等于最小滑块高度
                    raise ValueError("scroll_height must > slider_min")
                scroll_height = scroll_height  # 指定高度
        else:
            if expand:
                scroll_width = master.winfo_reqwidth()  # 滚动条宽度为父容器宽度
            else:
                if scroll_width <= slider_min:  # 宽度小于等于最小滑块宽度
                    raise ValueError("scroll_width must > slider_min")
                scroll_width = scroll_width  # 指定宽度
        self.scroll_size = [scroll_width, scroll_height]
        # canvas参数
        if scroll_bg is None:
            self["bg"] = master["bg"]  # 跟随父窗口背景色
        else:
            self["bg"] = scroll_bg  # 自定义背景色
        self.config(width=self.scroll_size[0], height=self.scroll_size[1], highlightthickness=0)
        # 滑块参数
        self.slider_init_pos: int = ...  # 滑块初始位置
        if self.orient == "v":  # 垂直滚动条
            # //大小
            if slider_width is ...:
                self.slider_width = self.scroll_size[0]  # 滑块宽度为滚动条宽度
            else:
                self.slider_width = slider_width
            self.slider_height = 0  # 需要后续再计算
            # //位置
            if slider_side == "left":
                self.slider_init_pos = 0
            elif slider_side == "right":
                self.slider_init_pos = self.scroll_size[0] - self.slider_width
            else:  # center
                self.slider_init_pos = (self.scroll_size[0] - self.slider_width) // 2
        else:  # 水平滚动条
            if slider_height is ...:
                self.slider_height = self.scroll_size[1]  # 滑块高度为滚动条高度
            else:
                self.slider_height = slider_height
            self.slider_width = 0
            if slider_side == "top":
                self.slider_init_pos = 0
            elif slider_side == "bottom":
                self.slider_init_pos = self.scroll_size[1] - self.slider_height
            else:
                self.slider_init_pos = (self.scroll_size[1] - self.slider_height) // 2
        # 其余参数
        self.expand = expand
        self.scroll_shorten = scroll_shorten
        self.init_step = step  # 初始步长
        self.step = step  # 变化的步长
        self.wheel_step = wheel_step
        self.slider_min = slider_min
        self.slider_bg = slider_bg
        self.focus_color = focus_color
        self.press_color = press_color
        # 回调函数
        self._command_enter = commands.get("enter", None)
        self._command_press = commands.get("press", None)
        self._command_release = commands.get("release", None)
        # 限制父容器最小尺寸
        master.minsize(slider_min * 2, slider_min * 2)
        # 绘制滚动条
        self.Scrollbar = self.create_rectangle(
            0, 0, self.scroll_size[0], self.scroll_size[1],
            fill=scroll_bg, width=0, tags="scrollbar",
        )
        # 绘制滑块
        if self.orient == "v":
            self.Slider = self.create_rectangle(
                self.slider_init_pos, 0, self.slider_width + self.slider_init_pos, self.slider_height,
                fill=self.slider_bg, width=0, tags="slider",
            )
        else:  # 水平滚动条
            self.Slider = self.create_rectangle(
                0, self.slider_init_pos, self.slider_width, self.slider_height + self.slider_init_pos,
                fill=self.slider_bg, width=0, tags="slider",
            )
        # 变量
        self.__in_sider = False  # 鼠标是否在滑块中
        self.__press_pos: list[int, int] = [0, 0]  # 鼠标点击位置
        self.__press = False  # 鼠标是否按下
        # 绑定
        self.bind("<Enter>", self.__enter)  # 鼠标进入
        self.bind("<Motion>", self.__motion)  # 鼠标移动
        self.bind("<Leave>", self.__leave)  # 鼠标离开
        self.bind("<Button-1>", self.__click)  # 鼠标左键按下
        self.bind("<ButtonRelease-1>", self.__release)  # 鼠标左键释放
        self.bind("<Configure>", self.__on_resize)  # 画布大小改变
        if self.expand:  # add=True表示不覆盖上一个绑定
            self.__master_bind_configure_id = self.master.bind("<Configure>", self.__on_master_resize, add=True)
        self.bind("<MouseWheel>", self.__on_wheel)  # 滚轮滚动
        self.bind("<Destroy>", self.__on_destroy)
        self.after(20, self.__calc)  # 延迟20ms后计算，等待画布初始化

    # 绑定画布
    def bind_canvas(self, canvas: "IkCanvas") -> bool:
        """
        绑定画布，必须是IkCanvas
        :param canvas: 画布
        :return: 绑定成功返回True，否则返回False
        """
        if self.canvas is None:
            if not isinstance(canvas, IkCanvas):  # 绑定的画布必须是IkCanvas
                raise TypeError("canvas必须是IkCanvas")
            self.canvas = canvas
            return True
        return False

    # 画布大小改变
    def __on_resize(self, event):
        self.__calc()

    # 父容器大小改变
    def __on_master_resize(self, event):
        direction = self.scroll_shorten[0]
        distance = self.scroll_shorten[1]
        width = self.master.winfo_width()
        height = self.master.winfo_height()
        if self.orient == "v":   # 垂直滚动条才处理高度
            height -= distance
        else:   # 水平滚动条才处理宽度
            width -= distance
        self.scroll_size = [width, height]
        if self.orient == "v":
            self.config(height=height)
            if direction == "up":
                self.coords("scrollbar", 0, distance, width, height + distance)
            else:
                self.coords("scrollbar", 0, 0, width, height)
        else:
            self.config(width=width)
            if direction == "left":
                self.coords("scrollbar", distance, 0, width + distance, height)
            else:
                self.coords("scrollbar", 0, 0, width, height)

    # 计算滑块大小
    def __calc(self):
        if self.canvas is None: return  # 未绑定画布
        pos_x, pos_y = 0, 0  # 滑块位置
        if self.orient == "v":
            if self.canvas.y_scroll is not self:  # 未绑定画布或画布未绑定本滚动条
                self.slider_height = self.scroll_size[1]  # 滑块高度为滚动条高度
                self._draw_slider(0, 0)
                return
            self.slider_height = self.scroll_size[1] - self.canvas.get_count[1] / self.init_step
            if self.slider_height < self.slider_min:  # 小于最小滑块高度
                self.slider_height = self.slider_min
                # 步长 = canvas可移动距离 / (滑块高度 - 最小滑块高度)
                self.step = self.canvas.get_count[1] / (self.scroll_size[1] - self.slider_min)
                pos_y = self.canvas.get_moved_count[1] / self.step
            else:  # 正常高度
                pos_y = self.coords("slider")[1]
                self.step = self.init_step  # 步长恢复初始值
        else:  # 水平滚动条
            if self.canvas.x_scroll is not self:
                self.slider_width = self.scroll_size[0]
                self._draw_slider(0, 0)
                return
            self.slider_width = self.scroll_size[0] - self.canvas.get_count[0] / self.init_step
            if self.slider_width < self.slider_min:  # 小于最小滑块宽度
                self.slider_width = self.slider_min
                self.step = self.canvas.get_count[0] / (self.scroll_size[0] - self.slider_min)
                pos_x = self.canvas.get_moved_count[0] / self.step
            else:  # 正常宽度
                pos_x = self.coords("slider")[0]
                self.step = self.init_step
        self._draw_slider(pos_x, pos_y)

    # 绘制滑块
    def _draw_slider(self, x: int | float, y: int | float):
        """
        绘制滑块
        :param x: 水平滚动条时有效
        :param y: 垂直滚动条时有效
        """
        if self.orient == "v":
            self.coords(
                "slider",
                self.slider_init_pos, y,
                self.slider_init_pos + self.slider_width, self.slider_height + y
            )
        else:
            self.coords(
                "slider",
                x, self.slider_init_pos,
                x + self.slider_width, self.slider_height + self.slider_init_pos
            )

    def __enter(self, event):
        if self._command_enter is not None:  # 进入的回调函数
            self._command_enter()

    def __motion(self, event):
        if self.canvas is None: return  # 未绑定画布
        if self.__press:  # 鼠标按下，移动滑块
            if self.orient == "v":
                if self.canvas.y_scroll is not self: return  # 画布未绑定本滚动条
                move_y = event.y - self.__press_pos[1]
                self.canvas.move(0, -move_y * self.step)  # 移动画布，且会自动移动滑块
            else:
                if self.canvas.x_scroll is not self: return  # 画布未绑定本滚动条
                move_x = event.x - self.__press_pos[0]
                self.canvas.move(-move_x * self.step, 0)
            self.__press_pos = [event.x, event.y]
        else:
            slider_info = self.coords("slider")
            # 鼠标在滑块中
            if slider_info[0] <= event.x <= slider_info[2] and slider_info[1] <= event.y <= slider_info[3]:
                self.itemconfig("slider", fill=self.focus_color)
                self.__in_sider = True
            else:  # 恢复默认颜色
                self.itemconfig("slider", fill=self.slider_bg)
                self.__in_sider = False

    def __leave(self, event):
        if not self.__press:
            self.itemconfig("slider", fill=self.slider_bg)
            self.__in_sider = False

    def __click(self, event):
        if self.__in_sider:
            self.__press = True
            self.__press_pos = [event.x, event.y]
            self.itemconfig("slider", fill=self.press_color)
            if self._command_press is not None:  # 按下的回调函数
                self._command_press()

    def __release(self, event):
        if self.__press:
            self.__press = False
            self.itemconfig("slider", fill=self.focus_color)
            if self._command_release is not None:  # 释放的回调函数
                self._command_release()

    def __on_wheel(self, event):
        if self.canvas is None: return
        wheel = self.wheel_step * -event.delta / 120
        if self.orient == "v":  # 垂直滚动条
            if self.canvas.y_scroll is not self:  # 未绑定本滚动条
                return
            self.canvas.move(0, -wheel)
        else:  # 水平滚动条
            if self.canvas.x_scroll is not self:  # 未绑定本滚动条
                return
            self.canvas.move(-wheel, 0)

    def __on_destroy(self, event):
        if self.canvas is not None:
            if self.orient == "v":
                self.canvas.y_scroll = None  # 解绑绑定
            else:  # 水平滚动条
                self.canvas.x_scroll = None  # 解绑绑定
        self.unbind("<Enter>")
        self.unbind("<Motion>")
        self.unbind("<Leave>")
        self.unbind("<Button-1>")
        self.unbind("<ButtonRelease-1>")
        self.unbind("<Configure>")
        if self.expand:
            self.master.unbind("<Configure>", self.__master_bind_configure_id)
        self.unbind("<MouseWheel>")
        self.unbind("<Destroy>")

    # 外部调用，移动滑块
    def move_slider(self, x, y):
        self._draw_slider(x / self.step, y / self.step)
