import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
plt.rcParams['font.sans-serif'] = ['SimHei']  # 用来正常显示中文标签
plt.rcParams['axes.unicode_minus'] = False  # 用来正常显示负号

class Component:
    def __init__(self, name, mass, x_g, y_g, z_g, buoyancy_data_file=None):
        self.name = name
        self.mass = mass
        # 将输入的质心坐标从mm转换为m
        self.x_g = x_g / 1000.0  # mm转m
        self.y_g = y_g / 1000.0  # mm转m
        self.z_g = z_g / 1000.0  # mm转m
        self.buoyancy_data_file = buoyancy_data_file
        self.buoyancy_data = None
        
    def load_buoyancy_data(self):
        try:
            # 读取文件数据
            data = []
            with open(self.buoyancy_data_file, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                # 跳过标题行
                for line in lines[2:]:
                    if not line.strip():  # 跳过空行
                        continue
                    try:
                        # 清理和分割行数据
                        line = line.strip()
                        # 移除所有括号和逗号
                        line = line.replace('(', '').replace(')', '').replace(',', ' ')
                        # 替换全角负号为半角负号
                        line = line.replace('−', '-')
                        # 分割并过滤掉空字符串
                        parts = [p for p in line.split() if p.strip()]
                        
                        if len(parts) < 5:
                            print(f"警告：跳过格式不正确的行: {line}")
                            continue
                            
                        # 处理角度
                        angle = float(parts[0].replace('°', ''))
                        # 处理浮力（单位：N）
                        buoyancy = float(parts[1])
                        # 处理坐标（单位：mm，需要转换为m）
                        x_b = float(parts[2]) / 1000.0  # mm转m
                        y_b = float(parts[3]) / 1000.0  # mm转m
                        z_b = float(parts[4]) / 1000.0  # mm转m
                        
                        data.append([angle, buoyancy, x_b, y_b, z_b])
                    except ValueError as ve:
                        print(f"警告：无法解析行: {line}, 错误: {str(ve)}")
                        continue
                    except Exception as e:
                        print(f"警告：处理行时出错: {line}, 错误: {str(e)}")
                        continue
            
            if not data:
                raise ValueError("没有读取到有效数据")
                
            self.buoyancy_data = pd.DataFrame(data, 
                columns=['angle', 'buoyancy', 'x_b', 'y_b', 'z_b'])
            print("成功读取数据：\n", self.buoyancy_data)
            return True
        except Exception as e:
            messagebox.showerror("错误", f"读取文件失败：{str(e)}\n文件格式应为：角度 浮力 X坐标(mm) Y坐标(mm) Z坐标(mm)\n示例：0° 650 1093 0 -89.4")
            return False

class RecoveryArmCalculator:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("船舶浮力体恢复力臂计算软件")
        self.root.geometry("1400x900")
        
        self.components = []
        self.setup_gui()
        
    def setup_gui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky="nsew")
        
        # 设置正向求解界面
        self.setup_forward_gui(main_frame)
        
        # 配置网格权重
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(1, weight=1)
        
    def setup_forward_gui(self, parent):
        """设置正向求解界面"""
        # 左侧面板 - 部件信息输入
        left_frame = ttk.Frame(parent, padding="5")
        left_frame.grid(row=0, column=0, sticky="nsew")
        
        # 部件输入区域
        input_frame = ttk.LabelFrame(left_frame, text="添加/编辑部件", padding="5")
        input_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        labels = ["部件名称:", "质量(kg):", "X质心(mm):", "Y质心(mm):", "Z质心(mm):"]
        self.entries = {}
        
        for i, label in enumerate(labels):
            ttk.Label(input_frame, text=label).grid(row=i, column=0, sticky="e", padx=5)
            self.entries[label] = ttk.Entry(input_frame)
            self.entries[label].grid(row=i, column=1, sticky="ew", padx=5)
        
        button_frame = ttk.Frame(input_frame)
        button_frame.grid(row=len(labels), column=0, columnspan=2, pady=5)
        
        ttk.Button(button_frame, text="选择浮力数据文件", 
                  command=self.select_file).grid(row=0, column=0, padx=5)
        
        ttk.Button(button_frame, text="添加部件", 
                  command=self.add_component).grid(row=0, column=1, padx=5)
        
        ttk.Button(button_frame, text="删除选中部件",
                  command=self.delete_component).grid(row=0, column=2, padx=5)
        
        # 已添加部件列表
        list_frame = ttk.LabelFrame(left_frame, text="已添加部件列表", padding="5")
        list_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        
        self.component_list = ttk.Treeview(list_frame, 
                                         columns=("名称", "质量", "X", "Y", "Z", "文件"),
                                         show="headings", height=10)
        
        # 设置列宽和标题
        self.component_list.column("名称", width=100)
        self.component_list.column("质量", width=80)
        self.component_list.column("X", width=80)
        self.component_list.column("Y", width=80)
        self.component_list.column("Z", width=80)
        self.component_list.column("文件", width=200)
        
        for col in self.component_list["columns"]:
            self.component_list.heading(col, text=col)
        
        # 添加滚动条
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical", 
                                command=self.component_list.yview)
        self.component_list.configure(yscrollcommand=scrollbar.set)
        
        self.component_list.grid(row=0, column=0, sticky="nsew")
        scrollbar.grid(row=0, column=1, sticky="ns")
        
        # 计算控制区域
        control_frame = ttk.LabelFrame(left_frame, text="计算控制", padding="5")
        control_frame.grid(row=2, column=0, sticky="ew", pady=5)
        
        # 自动计算开关
        self.auto_calc_var = tk.BooleanVar(value=True)
        ttk.Checkbutton(control_frame, text="自动计算", 
                       variable=self.auto_calc_var).grid(row=0, column=0, padx=5, pady=5)
        
        ttk.Button(control_frame, text="计算恢复力臂", 
                  command=self.calculate).grid(row=0, column=1, padx=5, pady=5)
        
        # 清空所有数据按钮
        ttk.Button(control_frame, text="清空所有数据", 
                  command=self.clear_all_data).grid(row=0, column=2, padx=5, pady=5)
        
        # 右侧面板 - 结果显示
        right_frame = ttk.Frame(parent, padding="5")
        right_frame.grid(row=0, column=1, sticky="nsew")
        
        # 结果数值显示区域
        result_frame = ttk.LabelFrame(right_frame, text="计算结果", padding="5")
        result_frame.grid(row=0, column=0, sticky="ew", pady=5)
        
        # 创建结果显示表格
        self.result_tree = ttk.Treeview(result_frame, 
                                      columns=("角度", "恢复力臂"),
                                      show="headings", height=5)
        self.result_tree.column("角度", width=100)
        self.result_tree.column("恢复力臂", width=100)
        self.result_tree.heading("角度", text="横倾角(°)")
        self.result_tree.heading("恢复力臂", text="恢复力臂(m)")
        
        result_scroll = ttk.Scrollbar(result_frame, orient="vertical", 
                                    command=self.result_tree.yview)
        self.result_tree.configure(yscrollcommand=result_scroll.set)
        
        self.result_tree.grid(row=0, column=0, sticky="nsew")
        result_scroll.grid(row=0, column=1, sticky="ns")
        
        # 创建图表
        plot_frame = ttk.LabelFrame(right_frame, text="恢复力臂曲线", padding="5")
        plot_frame.grid(row=1, column=0, sticky="nsew", pady=5)
        
        self.fig, self.ax = plt.subplots(figsize=(8, 6))
        self.canvas = FigureCanvasTkAgg(self.fig, master=plot_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # 配置网格权重
        parent.columnconfigure(1, weight=1)
        parent.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(1, weight=1)
        
    def select_file(self):
        filename = filedialog.askopenfilename(
            title="选择浮力数据文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")]
        )
        if filename:
            self.current_file = filename
            
    def clear_all_data(self):
        """清空所有数据和显示"""
        if messagebox.askyesno("确认", "确定要清空所有数据吗？"):
            # 清空部件列表
            self.components = []
            for item in self.component_list.get_children():
                self.component_list.delete(item)
            
            # 清空输入框
            for entry in self.entries.values():
                entry.delete(0, tk.END)
            
            # 清空结果表格
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
            
            # 清空图表
            self.ax.clear()
            self.ax.set_xlabel('横倾角 (度)')
            self.ax.set_ylabel('恢复力臂 (m)')
            self.ax.set_title('恢复力臂曲线')
            self.ax.grid(True)
            self.canvas.draw()
            
            # 重置文件选择
            if hasattr(self, 'current_file'):
                delattr(self, 'current_file')
    
    def add_component(self):
        try:
            # 验证输入
            name = self.entries["部件名称:"].get().strip()
            if not name:
                messagebox.showerror("错误", "请输入部件名称")
                return
                
            try:
                mass = float(self.entries["质量(kg):"].get())
                x_g = float(self.entries["X质心(mm):"].get())
                y_g = float(self.entries["Y质心(mm):"].get())
                z_g = float(self.entries["Z质心(mm):"].get())
            except ValueError:
                messagebox.showerror("错误", "请输入有效的数值")
                return
            
            if not hasattr(self, 'current_file'):
                messagebox.showerror("错误", "请选择浮力数据文件")
                return
                
            component = Component(name, mass, x_g, y_g, z_g, self.current_file)
            if component.load_buoyancy_data():
                self.components.append(component)
                self.component_list.insert("", "end", 
                    values=(name, mass, x_g, y_g, z_g, 
                           self.current_file.split("/")[-1]))
                
                # 清空输入框
                for entry in self.entries.values():
                    entry.delete(0, tk.END)
                
                # 如果开启了自动计算，则立即更新计算结果
                if self.auto_calc_var.get():
                    self.calculate()
                    
        except Exception as e:
            messagebox.showerror("错误", f"添加部件失败：{str(e)}")
            
    def delete_component(self):
        selected_items = self.component_list.selection()
        if not selected_items:
            messagebox.showwarning("警告", "请先选择要删除的部件")
            return
            
        if messagebox.askyesno("确认", "确定要删除选中的部件吗？"):
            for item in selected_items:
                index = self.component_list.index(item)
                self.component_list.delete(item)
                del self.components[index]
            
            # 如果开启了自动计算，则立即更新计算结果
            if self.auto_calc_var.get():
                self.calculate()
            
    def calculate(self):
        try:
            # 清空之前的结果
            for item in self.result_tree.get_children():
                self.result_tree.delete(item)
                
            if not self.components:
                # 如果没有部件，假设整体为一个浮力体
                if not hasattr(self, 'current_file'):
                    messagebox.showerror("错误", "请选择浮力数据文件")
                    return
                    
                # 创建一个临时组件用于计算，但不添加到self.components中
                temp_component = Component("整体", 1, 0, 0, 0, self.current_file)
                if not temp_component.load_buoyancy_data():
                    return
                    
                # 使用临时组件进行计算
                components_for_calc = [temp_component]
            else:
                # 使用已有组件进行计算
                components_for_calc = self.components
                
            # 计算总质量和质心
            total_mass = sum(c.mass for c in components_for_calc)
            z_g = sum(c.mass * c.z_g for c in components_for_calc) / total_mass if total_mass > 0 else 0
            
            # 获取第一个部件的角度列表作为基准
            angles = components_for_calc[0].buoyancy_data['angle'].values
            recovery_arms = []
            
            for angle in angles:
                # 计算该角度下的总浮力心
                total_buoyancy = 0
                weighted_y_b = 0
                weighted_z_b = 0
                
                for component in components_for_calc:
                    # 获取最接近的角度数据
                    angle_data = component.buoyancy_data.iloc[
                        (component.buoyancy_data['angle'] - angle).abs().argsort()[:1]
                    ]
                    
                    buoyancy = float(angle_data['buoyancy'])
                    y_b = float(angle_data['y_b'])
                    z_b = float(angle_data['z_b'])
                    
                    total_buoyancy += buoyancy
                    weighted_y_b += buoyancy * y_b
                    weighted_z_b += buoyancy * z_b
                
                y_b = weighted_y_b / total_buoyancy if total_buoyancy > 0 else 0
                z_b = weighted_z_b / total_buoyancy if total_buoyancy > 0 else 0
                
                # 计算恢复力臂
                phi = np.radians(angle)
                l = y_b * np.cos(phi) + z_b * np.sin(phi) - z_g * np.sin(phi)
                recovery_arms.append(round(l, 3))  # 增加精度到3位小数
                
                # 更新结果表格
                self.result_tree.insert("", "end", values=(angle, round(l, 3)))
            
            # 绘制结果
            self.ax.clear()
            
            # 添加零线
            self.ax.axhline(y=0, color='k', linestyle='-', alpha=0.3)
            
            # 绘制恢复力臂曲线
            self.ax.plot(angles, recovery_arms, 'b-', linewidth=2)
            
            # 设置坐标轴标签和标题
            self.ax.set_xlabel('横倾角 (度)')
            self.ax.set_ylabel('恢复力臂 (m)')
            self.ax.set_title('恢复力臂曲线')
            self.ax.grid(True)
            
            # 找出最大正值和最小负值
            max_positive_arm = max(recovery_arms)
            min_negative_arm = min(recovery_arms)
            max_positive_angle = angles[recovery_arms.index(max_positive_arm)]
            min_negative_angle = angles[recovery_arms.index(min_negative_arm)]
            
            # 标注最大正值点
            if max_positive_arm > 0:
                self.ax.plot(max_positive_angle, max_positive_arm, 'ro')
                self.ax.annotate(f'最大正值: {max_positive_arm}m\n角度: {max_positive_angle}°',
                                xy=(max_positive_angle, max_positive_arm), 
                                xytext=(10, 10),
                                textcoords='offset points')
            
            # 标注最小负值点
            if min_negative_arm < 0:
                self.ax.plot(min_negative_angle, min_negative_arm, 'ro')
                self.ax.annotate(f'最小负值: {min_negative_arm}m\n角度: {min_negative_angle}°',
                                xy=(min_negative_angle, min_negative_arm), 
                                xytext=(10, -20),
                                textcoords='offset points')
            
            # 自动调整Y轴范围，确保包含所有数据点并留有一定边距
            y_range = max_positive_arm - min_negative_arm
            y_margin = y_range * 0.1  # 10%的边距
            self.ax.set_ylim(min_negative_arm - y_margin, max_positive_arm + y_margin)
            
            self.canvas.draw()
            
        except Exception as e:
            messagebox.showerror("计算错误", f"计算过程中出现错误：{str(e)}")
            # 发生错误时清空图表
            self.ax.clear()
            self.ax.set_xlabel('横倾角 (度)')
            self.ax.set_ylabel('恢复力臂 (m)')
            self.ax.set_title('恢复力臂曲线')
            self.ax.grid(True)
            self.canvas.draw()
        
    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = RecoveryArmCalculator()
    app.run() 