import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import uuid
import time
import logging
import os
from .core import ThreadMaster, ThreadPriority, ThreadStatus

logger = logging.getLogger("ThreadMaster")

class ThreadMonitorGUI:
    """GUI for thread monitoring and management"""
    
    def __init__(self, master=None):
        self.thread_master = ThreadMaster()
        
        # Example threads/tasks
        self.demo_tasks = {
            "CPU Bound": self._cpu_bound_task,
            "IO Bound": self._io_bound_task,
            "Exception Task": self._exception_task,
            "Random Sleep": self._random_sleep_task,
            "Counter Task": self._counter_task
        }
        
        # Create the main window if not provided
        if master:
            self.root = master
        else:
            self.root = tk.Tk()
            
        self.root.title("ThreadMaster - Thread Management System")
        self.root.geometry("1280x720")
        self.root.minsize(800, 600)
        
        # Theme State
        self.dark_mode = False
        
        # Configure Initial Theme
        self.style = ttk.Style()
        self.style.theme_use("clam")
        self._apply_light_theme()
        
        # Create the main frame
        self.main_frame = ttk.Frame(self.root)
        self.main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.main_frame)
        self.notebook.pack(fill=tk.BOTH, expand=True)
        
        # Create tabs
        self.dashboard_tab = ttk.Frame(self.notebook)
        self.threads_tab = ttk.Frame(self.notebook)
        self.groups_tab = ttk.Frame(self.notebook)
        self.create_tab = ttk.Frame(self.notebook)
        self.system_tab = ttk.Frame(self.notebook)
        
        self.notebook.add(self.dashboard_tab, text="Dashboard")
        self.notebook.add(self.threads_tab, text="Threads")
        self.notebook.add(self.groups_tab, text="Groups")
        self.notebook.add(self.create_tab, text="Create")
        self.notebook.add(self.system_tab, text="System")
        
        # Setup each tab
        self._setup_dashboard_tab()
        self._setup_threads_tab()
        self._setup_groups_tab()
        self._setup_create_tab()
        self._setup_system_tab()
        
        # Add Theme Toggle
        self._setup_theme_toggle()
        
        # Start resource tracking
        self.thread_master.start_resource_tracking()
        
        # Setup auto-refresh
        self.refresh_interval = 1000  # ms
        self.root.after(self.refresh_interval, self._auto_refresh)
        
        logger.info("ThreadMonitorGUI initialized")
        
    def _apply_light_theme(self):
        """Apply light theme colors"""
        self.bg_color = "#f5f5f5"
        self.fg_color = "black"
        self.text_bg = "white"
        
        self.style.configure("TButton", padding=6, relief="flat",
                           background="#4CAF50", foreground="black")
        self.style.configure("Danger.TButton", padding=6, relief="flat",
                           background="#f44336", foreground="white")
        self.style.configure("Warning.TButton", padding=6, relief="flat", 
                           background="#ff9800", foreground="black")
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TNotebook", background=self.bg_color)
        self.style.configure("TNotebook.Tab", padding=[12, 4],
                           background="#e0e0e0", foreground="black")
        self.style.map("TNotebook.Tab", background=[("selected", "#4CAF50")],
                     foreground=[("selected", "white")])
        self.style.configure("Treeview", background="white", foreground="black", fieldbackground="white")
        
        self.root.configure(bg=self.bg_color)
        if hasattr(self, 'main_frame'):
            self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
            self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.fg_color)

    def _apply_dark_theme(self):
        """Apply dark theme colors"""
        self.bg_color = "#2d2d2d"
        self.fg_color = "#ffffff"
        self.text_bg = "#1e1e1e"
        
        self.style.configure("TButton", padding=6, relief="flat",
                           background="#388E3C", foreground="white")
        self.style.configure("Danger.TButton", padding=6, relief="flat",
                           background="#d32f2f", foreground="white")
        self.style.configure("Warning.TButton", padding=6, relief="flat", 
                           background="#f57c00", foreground="white")
        self.style.configure("TFrame", background=self.bg_color)
        self.style.configure("TNotebook", background=self.bg_color)
        self.style.configure("TNotebook.Tab", padding=[12, 4],
                           background="#424242", foreground="white")
        self.style.map("TNotebook.Tab", background=[("selected", "#388E3C")],
                     foreground=[("selected", "white")])
        self.style.configure("Treeview", background="#424242", foreground="white", fieldbackground="#424242")
        self.style.configure("TLabel", background=self.bg_color, foreground=self.fg_color)
        self.style.configure("TLabelframe", background=self.bg_color, foreground=self.fg_color)
        self.style.configure("TLabelframe.Label", background=self.bg_color, foreground=self.fg_color)
        
        self.root.configure(bg=self.bg_color)
        
    def _toggle_theme(self):
        """Toggle between light and dark mode"""
        self.dark_mode = not self.dark_mode
        if self.dark_mode:
            self._apply_dark_theme()
            self.theme_btn.config(text="☀ Light Mode")
        else:
            self._apply_light_theme()
            self.theme_btn.config(text="🌙 Dark Mode")
        self._update_charts() # Redraw charts to match theme

    def _setup_theme_toggle(self):
        """Add theme toggle button to dashboard"""
        # We'll add it to the button frame in dashboard, but simpler: put it in bottom right of window
        self.theme_btn = tk.Button(self.root, text="🌙 Dark Mode", command=self._toggle_theme, width=12)
        self.theme_btn.place(relx=1.0, rely=0.0, anchor="ne", x=-10, y=5)

    def _setup_dashboard_tab(self):
        """Setup the dashboard tab"""
        # Create frames
        stats_frame = ttk.Frame(self.dashboard_tab)
        stats_frame.pack(fill=tk.X, pady=10)
        
        # Statistics section
        ttk.Label(stats_frame, text="Thread Statistics", font=('Arial', 14, 'bold')).pack(anchor=tk.W)
        
        # Stats display
        self.stats_display = ttk.Frame(stats_frame)
        self.stats_display.pack(fill=tk.X, pady=5)
        
        # Thread counts
        self.thread_counts = {
            "Total": tk.StringVar(value="0"),
            "Running": tk.StringVar(value="0"),
            "Waiting": tk.StringVar(value="0"),
            "Completed": tk.StringVar(value="0"),
            "Failed": tk.StringVar(value="0")
        }
        
        col = 0
        for label, var in self.thread_counts.items():
            frame = ttk.Frame(self.stats_display)
            frame.grid(row=0, column=col, padx=10)
            
            ttk.Label(frame, text=label).pack()
            ttk.Label(frame, textvariable=var, font=('Arial', 16, 'bold')).pack()
            
            col += 1
            
        # Charts section
        charts_frame = ttk.Frame(self.dashboard_tab)
        charts_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        # CPU and memory usage charts
        chart_left = ttk.Frame(charts_frame)
        chart_left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        chart_right = ttk.Frame(charts_frame)
        chart_right.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # CPU usage chart
        ttk.Label(chart_left, text="CPU Usage", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.cpu_figure = plt.Figure(figsize=(5, 3), dpi=100)
        self.cpu_plot = self.cpu_figure.add_subplot(111)
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_figure, chart_left)
        self.cpu_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Memory usage chart
        ttk.Label(chart_right, text="Memory Usage", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        self.memory_figure = plt.Figure(figsize=(5, 3), dpi=100)
        self.memory_plot = self.memory_figure.add_subplot(111)
        self.memory_canvas = FigureCanvasTkAgg(self.memory_figure, chart_right)
        self.memory_canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Recent activity section
        activity_frame = ttk.Frame(self.dashboard_tab)
        activity_frame.pack(fill=tk.BOTH, expand=True, pady=10)
        
        ttk.Label(activity_frame, text="Recent Activity", font=('Arial', 12, 'bold')).pack(anchor=tk.W)
        
        # Activity log
        self.activity_log = scrolledtext.ScrolledText(activity_frame, height=8)
        self.activity_log.pack(fill=tk.BOTH, expand=True, pady=5)
        self.activity_log.config(state=tk.DISABLED)
        
        # Action buttons
        button_frame = ttk.Frame(self.dashboard_tab)
        button_frame.pack(fill=tk.X, pady=10)
        
        ttk.Button(button_frame, text="Refresh", command=self._refresh_dashboard).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Create Demo Threads", command=self._create_demo_threads).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Clean Up Completed", command=self._cleanup_completed).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Terminate All", command=self._terminate_all, style="Danger.TButton").pack(side=tk.RIGHT, padx=5)
            
    def _setup_threads_tab(self):
        """Setup the threads tab"""
        # Controls
        controls_frame = ttk.Frame(self.threads_tab)
        controls_frame.pack(fill=tk.X, pady=5)
        
        ttk.Label(controls_frame, text="Filter:").pack(side=tk.LEFT, padx=5)
        self.thread_filter = ttk.Combobox(controls_frame, values=["All", "Running", "Waiting", "Completed", "Failed", "Terminated"])
        self.thread_filter.pack(side=tk.LEFT, padx=5)
        self.thread_filter.current(0)
        self.thread_filter.bind("<<ComboboxSelected>>", lambda e: self._refresh_threads())
        
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_threads).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Terminate Selected", command=self._terminate_selected_thread, style="Warning.TButton").pack(side=tk.RIGHT, padx=5)
        
        # Thread list
        list_frame = ttk.Frame(self.threads_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Thread list with scroll
        columns = ("ID", "Name", "Status", "Priority", "Runtime", "Group")
        self.thread_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Configure headings
        for col in columns:
            self.thread_tree.heading(col, text=col)
            
        # Configure column widths
        self.thread_tree.column("ID", width=80)
        self.thread_tree.column("Name", width=150)
        self.thread_tree.column("Status", width=100)
        self.thread_tree.column("Priority", width=100)
        self.thread_tree.column("Runtime", width=100)
        self.thread_tree.column("Group", width=150)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.thread_tree.yview)
        self.thread_tree.configure(yscrollcommand=vsb.set)
        
        # Add horizontal scrollbar
        hsb = ttk.Scrollbar(list_frame, orient="horizontal", command=self.thread_tree.xview)
        self.thread_tree.configure(xscrollcommand=hsb.set)
        
        # Pack everything
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        hsb.pack(side=tk.BOTTOM, fill=tk.X)
        self.thread_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click to view details
        self.thread_tree.bind("<Double-1>", self._show_thread_details)
            
    def _setup_groups_tab(self):
        """Setup the groups tab"""
        # Controls
        controls_frame = ttk.Frame(self.groups_tab)
        controls_frame.pack(fill=tk.X, pady=5)
        
        ttk.Button(controls_frame, text="Refresh", command=self._refresh_groups).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Create Group", command=self._create_new_group).pack(side=tk.LEFT, padx=5)
        ttk.Button(controls_frame, text="Terminate Group", command=self._terminate_selected_group, style="Warning.TButton").pack(side=tk.RIGHT, padx=5)
        
        # Group list
        list_frame = ttk.Frame(self.groups_tab)
        list_frame.pack(fill=tk.BOTH, expand=True, pady=5)
        
        # Group list with scroll
        columns = ("Name", "Thread Count", "Running", "Waiting", "Completed", "Failed")
        self.group_tree = ttk.Treeview(list_frame, columns=columns, show="headings")
        
        # Configure headings
        for col in columns:
            self.group_tree.heading(col, text=col)
            
        # Configure column widths
        self.group_tree.column("Name", width=150)
        self.group_tree.column("Thread Count", width=100)
        self.group_tree.column("Running", width=100)
        self.group_tree.column("Waiting", width=100)
        self.group_tree.column("Completed", width=100)
        self.group_tree.column("Failed", width=100)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(list_frame, orient="vertical", command=self.group_tree.yview)
        self.group_tree.configure(yscrollcommand=vsb.set)
        
        # Pack everything
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.group_tree.pack(fill=tk.BOTH, expand=True)
        
        # Bind double-click to view details
        self.group_tree.bind("<Double-1>", self._show_group_details)
            
    def _setup_create_tab(self):
        """Setup the create tab"""
        # Main frame with padding
        main_frame = ttk.Frame(self.create_tab, padding=10)
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Create thread section
        thread_frame = ttk.LabelFrame(main_frame, text="Create Thread", padding=10)
        thread_frame.pack(fill=tk.X, pady=10)
        
        # Thread parameters
        param_frame = ttk.Frame(thread_frame)
        param_frame.pack(fill=tk.X)
        
        # Thread name
        ttk.Label(param_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_name_var = tk.StringVar()
        ttk.Entry(param_frame, textvariable=self.thread_name_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Thread group
        ttk.Label(param_frame, text="Group:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_group_var = tk.StringVar()
        self.thread_group_combo = ttk.Combobox(param_frame, textvariable=self.thread_group_var)
        self.thread_group_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Thread priority
        ttk.Label(param_frame, text="Priority:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_priority_var = tk.StringVar(value="NORMAL")
        ttk.Combobox(param_frame, textvariable=self.thread_priority_var, 
                    values=["LOW", "NORMAL", "HIGH", "CRITICAL"]).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Thread type
        ttk.Label(param_frame, text="Type:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.thread_type_var = tk.StringVar(value="CPU Bound")
        self.thread_type_combo = ttk.Combobox(param_frame, textvariable=self.thread_type_var, 
                                             values=list(self.demo_tasks.keys()))
        self.thread_type_combo.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Parameters for the task
        ttk.Label(param_frame, text="Duration (s):").grid(row=4, column=0, sticky=tk.W, padx=5, pady=5)
        self.task_duration_var = tk.StringVar(value="5")
        ttk.Entry(param_frame, textvariable=self.task_duration_var).grid(row=4, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Create button
        button_frame = ttk.Frame(thread_frame)
        button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(button_frame, text="Create Thread", command=self._create_thread).pack(side=tk.RIGHT)
        
        # Set column weights
        param_frame.columnconfigure(1, weight=1)
        
        # Create group section
        group_frame = ttk.LabelFrame(main_frame, text="Create Group", padding=10)
        group_frame.pack(fill=tk.X, pady=10)
        
        # Group parameters
        group_param_frame = ttk.Frame(group_frame)
        group_param_frame.pack(fill=tk.X)
        
        # Group name
        ttk.Label(group_param_frame, text="Name:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.group_name_var = tk.StringVar()
        ttk.Entry(group_param_frame, textvariable=self.group_name_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Group description
        ttk.Label(group_param_frame, text="Description:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.group_desc_var = tk.StringVar()
        ttk.Entry(group_param_frame, textvariable=self.group_desc_var).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Create button
        group_button_frame = ttk.Frame(group_frame)
        group_button_frame.pack(fill=tk.X, pady=10)
        ttk.Button(group_button_frame, text="Create Group", command=self._create_group).pack(side=tk.RIGHT)
        
        # Set column weights
        group_param_frame.columnconfigure(1, weight=1)
            
    def _setup_system_tab(self):
        """Setup the system tab"""
        # System info section
        info_frame = ttk.LabelFrame(self.system_tab, text="System Information", padding=10)
        info_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # System stats
        self.cpu_label = ttk.Label(info_frame, text="CPU Usage: -")
        self.cpu_label.pack(anchor=tk.W, pady=2)
        
        self.memory_label = ttk.Label(info_frame, text="Memory Usage: -")
        self.memory_label.pack(anchor=tk.W, pady=2)
        
        self.thread_count_label = ttk.Label(info_frame, text="Thread Count: -")
        self.thread_count_label.pack(anchor=tk.W, pady=2)
        
        # Thread pool section
        pool_frame = ttk.LabelFrame(self.system_tab, text="Thread Pool", padding=10)
        pool_frame.pack(fill=tk.X, pady=10, padx=10)
        
        # Thread pool controls
        pool_controls = ttk.Frame(pool_frame)
        pool_controls.pack(fill=tk.X)
        
        ttk.Label(pool_controls, text="Max Workers:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.pool_workers_var = tk.StringVar(value=str(os.cpu_count()))
        ttk.Entry(pool_controls, textvariable=self.pool_workers_var, width=10).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        ttk.Label(pool_controls, text="Pool Name:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.pool_name_var = tk.StringVar(value="WorkerPool")
        ttk.Entry(pool_controls, textvariable=self.pool_name_var).grid(row=0, column=3, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Button(pool_controls, text="Create Pool", command=self._create_pool).grid(row=0, column=4, padx=5, pady=5)
        
        # Set column weights
        pool_controls.columnconfigure(3, weight=1)
        
        # Pool list
        ttk.Label(pool_frame, text="Active Pools:").pack(anchor=tk.W, pady=5)
        
        pool_list_frame = ttk.Frame(pool_frame)
        pool_list_frame.pack(fill=tk.BOTH, expand=True)
        
        columns = ("Name", "Workers", "Queue Size", "Completed", "Failed", "Total")
        self.pool_tree = ttk.Treeview(pool_list_frame, columns=columns, show="headings", height=5)
        
        # Configure headings
        for col in columns:
            self.pool_tree.heading(col, text=col)
            
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(pool_list_frame, orient="vertical", command=self.pool_tree.yview)
        self.pool_tree.configure(yscrollcommand=vsb.set)
        
        # Pack everything
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        self.pool_tree.pack(fill=tk.BOTH, expand=True)
        
        # Logging section
        log_frame = ttk.LabelFrame(self.system_tab, text="System Log", padding=10)
        log_frame.pack(fill=tk.BOTH, expand=True, pady=10, padx=10)
        
        # Log level control
        log_control = ttk.Frame(log_frame)
        log_control.pack(fill=tk.X)
        
        ttk.Label(log_control, text="Log Level:").pack(side=tk.LEFT, padx=5)
        self.log_level_var = tk.StringVar(value="INFO")
        ttk.Combobox(log_control, textvariable=self.log_level_var, 
                     values=["DEBUG", "INFO", "WARNING", "ERROR"]).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control, text="Apply", command=self._set_log_level).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_control, text="Clear Log", command=self._clear_log).pack(side=tk.RIGHT, padx=5)
        
        # Log display
        self.system_log = scrolledtext.ScrolledText(log_frame)
        self.system_log.pack(fill=tk.BOTH, expand=True, pady=5)
        self.system_log.config(state=tk.DISABLED)
            
    def _auto_refresh(self):
        """Auto refresh the UI"""
        try:
            self._refresh_dashboard()
            self._refresh_system_tab()
        except tk.TclError:
            pass  # Window likely closed
        
        # Schedule next refresh
        if self.root.winfo_exists():
            self.root.after(self.refresh_interval, self._auto_refresh)
        
    def _refresh_dashboard(self):
        """Refresh the dashboard"""
        # Update thread statistics
        stats = self.thread_master.get_thread_stats()
        self.thread_counts["Total"].set(str(stats["total"]))
        self.thread_counts["Running"].set(str(stats["running"]))
        self.thread_counts["Waiting"].set(str(stats["waiting"]))
        self.thread_counts["Completed"].set(str(stats["completed"]))
        self.thread_counts["Failed"].set(str(stats["failed"]))
        
        # Update charts
        self._update_charts()
        
    def _refresh_threads(self):
        """Refresh the threads list"""
        # Clear the list
        for item in self.thread_tree.get_children():
            self.thread_tree.delete(item)
            
        # Get current filter
        filter_status = self.thread_filter.get()
        
        # Add threads to the list
        for thread_id, thread in self.thread_master.threads.items():
            # Apply filter
            if filter_status != "All" and thread.status.name != filter_status:
                continue
                
            # Add to tree
            self.thread_tree.insert("", tk.END, values=(
                thread_id[:8],
                thread.name,
                thread.status.name,
                thread.priority.name,
                f"{thread.get_runtime():.2f}s",
                thread.group.name if thread.group else "-"
            ))
            
    def _refresh_groups(self):
        """Refresh the groups list"""
        # Clear the list
        for item in self.group_tree.get_children():
            self.group_tree.delete(item)
            
        # Update the thread group combo in create tab
        self.thread_group_combo['values'] = [""] + list(self.thread_master.groups.keys())
        
        # Add groups to the list
        for name, group in self.thread_master.groups.items():
            stats = group.get_stats()
            
            self.group_tree.insert("", tk.END, values=(
                name,
                stats["total"],
                stats["running"],
                stats["waiting"],
                stats["completed"],
                stats["failed"]
            ))
            
    def _refresh_system_tab(self):
        """Refresh the system tab"""
        # Update system stats
        stats = self.thread_master.get_system_stats()
        self.cpu_label.config(text=f"CPU Usage: {stats['cpu_usage']:.1f}%")
        self.memory_label.config(text=f"Memory Usage: {stats['memory_percent']:.1f}% ({stats['memory_used'] / (1024**3):.1f} GB / {stats['memory_total'] / (1024**3):.1f} GB)")
        
        thread_stats = self.thread_master.get_thread_stats()
        self.thread_count_label.config(text=f"Thread Count: {thread_stats['total']} (Running: {thread_stats['running']}, Waiting: {thread_stats['waiting']})")
        
        # Update pool list
        self._refresh_pools()
        
    def _refresh_pools(self):
        """Refresh the pools list"""
        # Clear the list
        for item in self.pool_tree.get_children():
            self.pool_tree.delete(item)
            
        # Add pools to the list
        for pool_id, pool in self.thread_master.pools.items():
            stats = pool.get_stats()
            
            self.pool_tree.insert("", tk.END, values=(
                stats["name"],
                stats["max_workers"],
                stats["queue_size"],
                stats["completed_tasks"],
                stats["failed_tasks"],
                stats["total_tasks"]
            ))
            
    def _update_charts(self):
        """Update the charts"""
        # Get system stats
        stats = self.thread_master.get_system_stats()
        
        # Chart Colors based on theme
        bg = self.bg_color if self.dark_mode else 'white'
        params = {"facecolor": bg} 
        self.cpu_figure.set_facecolor(bg)
        self.memory_figure.set_facecolor(bg)
        
        text_color = "white" if self.dark_mode else "black"
        
        # CPU chart
        self.cpu_plot.clear()
        self.cpu_plot.set_facecolor(bg)
        
        if stats["cpu_history"]:
            times, values = zip(*stats["cpu_history"])
            relative_times = [t - times[0] for t in times]
            self.cpu_plot.plot(relative_times, values, 'b-', label='CPU')
            self.cpu_plot.set_ylim(0, 100)
            self.cpu_plot.set_xlabel("Time (s)", color=text_color)
            self.cpu_plot.set_ylabel("CPU (%)", color=text_color)
            self.cpu_plot.tick_params(colors=text_color)
            self.cpu_plot.grid(True, linestyle="--", alpha=0.3)
            
        self.cpu_canvas.draw()
        
        # Memory chart
        self.memory_plot.clear()
        self.memory_plot.set_facecolor(bg)
        
        if stats["memory_history"]:
            times, values = zip(*stats["memory_history"])
            relative_times = [t - times[0] for t in times]
            self.memory_plot.plot(relative_times, values, 'r-', label='RAM')
            self.memory_plot.set_ylim(0, 100)
            self.memory_plot.set_xlabel("Time (s)", color=text_color)
            self.memory_plot.set_ylabel("Memory (%)", color=text_color)
            self.memory_plot.tick_params(colors=text_color)
            self.memory_plot.grid(True, linestyle="--", alpha=0.3)
            
        self.memory_canvas.draw()
        
    def _create_demo_threads(self):
        """Create some demo threads"""
        group = self.thread_master.create_group("DemoGroup", "Demo threads group")
        
        # Create a variety of threads
        for i, task_type in enumerate(self.demo_tasks.keys()):
            self.thread_master.create_thread(
                target=self.demo_tasks[task_type],
                args=(5,),  # 5 seconds duration
                name=f"Demo-{task_type}-{i}",
                priority=ThreadPriority.NORMAL,
                group=group,
                auto_start=True
            )
            
        self._log_activity(f"Created demo threads in group 'DemoGroup'")
        self._refresh_threads()
        self._refresh_groups()
        
    def _cleanup_completed(self):
        """Clean up completed threads"""
        count = self.thread_master.cleanup_completed()
        self._log_activity(f"Cleaned up {count} completed threads")
        self._refresh_threads()
        self._refresh_groups()
        
    def _terminate_all(self):
        """Terminate all threads"""
        result = messagebox.askokcancel("Terminate All", "Are you sure you want to terminate all threads?")
        if result:
            self.thread_master.terminate_all()
            self._log_activity("Terminated all threads")
            self._refresh_threads()
            self._refresh_groups()
            
    def _terminate_selected_thread(self):
        """Terminate the selected thread"""
        selected = self.thread_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a thread to terminate.")
            return
            
        thread_id = self.thread_tree.item(selected[0])['values'][0]
        
        # Find the full thread ID
        full_id = None
        for tid in self.thread_master.threads.keys():
            if tid.startswith(thread_id):
                full_id = tid
                break
                
        if full_id:
            thread = self.thread_master.get_thread(full_id)
            if thread:
                thread.terminate()
                self._log_activity(f"Terminated thread: {thread.name}")
                self._refresh_threads()
                
    def _terminate_selected_group(self):
        """Terminate the selected group"""
        selected = self.group_tree.selection()
        if not selected:
            messagebox.showinfo("No Selection", "Please select a group to terminate.")
            return
            
        group_name = self.group_tree.item(selected[0])['values'][0]
        group = self.thread_master.get_group(group_name)
        
        if group:
            group.terminate_all()
            self._log_activity(f"Terminated all threads in group: {group_name}")
            self._refresh_threads()
            self._refresh_groups()
            
    def _create_thread(self):
        """Create a new thread with user input"""
        # Get parameters
        name = self.thread_name_var.get() or f"Thread-{uuid.uuid4().hex[:8]}"
        group_name = self.thread_group_var.get()
        priority_name = self.thread_priority_var.get()
        task_type = self.thread_type_var.get()
        
        try:
            duration = float(self.task_duration_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Duration must be a number.")
            return
            
        # Get the group if specified
        group = None
        if group_name:
            group = self.thread_master.get_group(group_name)
            if not group:
                group = self.thread_master.create_group(group_name)
                
        # Get the task function
        task_func = self.demo_tasks.get(task_type)
        if not task_func:
            messagebox.showerror("Invalid Task", "Please select a valid task type.")
            return
            
        # Get the priority
        priority = ThreadPriority.NORMAL
        try:
            priority = ThreadPriority[priority_name]
        except KeyError:
            pass
            
        # Create and start the thread
        thread = self.thread_master.create_thread(
            target=task_func,
            args=(duration,),
            name=name,
            priority=priority,
            group_name=group_name if group_name else None,
            auto_start=True
        )
        
        self._log_activity(f"Created thread: {name} ({task_type}, {duration}s)")
        self._refresh_threads()
        self._refresh_groups()
        
    def _create_group(self):
        """Create a new group with user input"""
        # Get parameters
        name = self.group_name_var.get()
        description = self.group_desc_var.get()
        
        if not name:
            messagebox.showerror("Invalid Input", "Group name is required.")
            return
            
        # Create the group
        group = self.thread_master.create_group(name, description)
        
        self._log_activity(f"Created group: {name}")
        self._refresh_groups()
        
        # Clear inputs
        self.group_name_var.set("")
        self.group_desc_var.set("")
        
    def _create_new_group(self):
        """Create a new group from the groups tab"""
        # Show a dialog to get group name
        dialog = tk.Toplevel(self.root)
        dialog.title("Create Group")
        dialog.geometry("300x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center on parent
        dialog.geometry("+{}+{}".format(
            self.root.winfo_x() + int(self.root.winfo_width()/2 - 150),
            self.root.winfo_y() + int(self.root.winfo_height()/2 - 75)
        ))
        
        # Create widgets
        ttk.Label(dialog, text="Group Name:").pack(pady=(15, 5))
        name_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=name_var).pack(fill=tk.X, padx=20, pady=5)
        
        ttk.Label(dialog, text="Description:").pack(pady=5)
        desc_var = tk.StringVar()
        ttk.Entry(dialog, textvariable=desc_var).pack(fill=tk.X, padx=20, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(dialog)
        button_frame.pack(fill=tk.X, padx=20, pady=15)
        
        def on_cancel():
            dialog.destroy()
            
        def on_create():
            name = name_var.get()
            desc = desc_var.get()
            
            if not name:
                messagebox.showerror("Invalid Input", "Group name is required.", parent=dialog)
                return
                
            self.thread_master.create_group(name, desc)
            self._log_activity(f"Created group: {name}")
            self._refresh_groups()
            dialog.destroy()
            
        ttk.Button(button_frame, text="Cancel", command=on_cancel).pack(side=tk.LEFT)
        ttk.Button(button_frame, text="Create", command=on_create).pack(side=tk.RIGHT)
        
    def _create_pool(self):
        """Create a new thread pool"""
        # Get parameters
        try:
            max_workers = int(self.pool_workers_var.get())
        except ValueError:
            messagebox.showerror("Invalid Input", "Max workers must be a number.")
            return
            
        name = self.pool_name_var.get() or "Pool"
        
        # Create the pool
        pool = self.thread_master.create_pool(max_workers, name)
        
        self._log_activity(f"Created thread pool: {name} with {max_workers} workers")
        self._refresh_pools()
        
    def _show_thread_details(self, event):
        """Show details for the selected thread"""
        selected = self.thread_tree.selection()
        if not selected:
            return
            
        thread_id = self.thread_tree.item(selected[0])['values'][0]
        
        # Find the full thread ID
        full_id = None
        for tid in self.thread_master.threads.keys():
            if tid.startswith(thread_id):
                full_id = tid
                break
                
        if full_id:
            thread = self.thread_master.get_thread(full_id)
            if thread:
                self._show_thread_dialog(thread)
                
    def _show_group_details(self, event):
        """Show details for the selected group"""
        selected = self.group_tree.selection()
        if not selected:
            return
            
        group_name = self.group_tree.item(selected[0])['values'][0]
        group = self.thread_master.get_group(group_name)
        
        if group:
            self._show_group_dialog(group)
            
    def _show_thread_dialog(self, thread):
        """Show a dialog with thread details"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Thread Details: {thread.name}")
        dialog.geometry("500x400")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center on parent
        dialog.geometry("+{}+{}".format(
            self.root.winfo_x() + int(self.root.winfo_width()/2 - 250),
            self.root.winfo_y() + int(self.root.winfo_height()/2 - 200)
        ))
        
        # Thread info
        info_frame = ttk.LabelFrame(dialog, text="Thread Information", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create grid for thread info
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, expand=True)
        
        # Add thread properties
        row = 0
        for label, value in [
            ("ID", thread.thread_id),
            ("Name", thread.name),
            ("Status", thread.status.name),
            ("Priority", thread.priority.name),
            ("Runtime", f"{thread.get_runtime():.2f} seconds"),
            ("Group", thread.group.name if thread.group else "None"),
            ("Started", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(thread.start_time)) if thread.start_time else "Not started"),
            ("Ended", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(thread.end_time)) if thread.end_time else "Running"),
        ]:
            ttk.Label(info_grid, text=f"{label}:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_grid, text=str(value)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            row += 1
            
        # Thread controls
        control_frame = ttk.Frame(dialog)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Add control buttons based on thread state
        if thread.status == ThreadStatus.RUNNING:
            ttk.Button(control_frame, text="Pause", command=lambda: self._pause_thread(thread, dialog)).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Terminate", command=lambda: self._terminate_thread(thread, dialog), style="Warning.TButton").pack(side=tk.LEFT, padx=5)
        elif thread.status == ThreadStatus.WAITING:
            ttk.Button(control_frame, text="Resume", command=lambda: self._resume_thread(thread, dialog)).pack(side=tk.LEFT, padx=5)
            ttk.Button(control_frame, text="Terminate", command=lambda: self._terminate_thread(thread, dialog), style="Warning.TButton").pack(side=tk.LEFT, padx=5)
            
        # Exception info if any
        if thread.exception:
            exc_frame = ttk.LabelFrame(dialog, text="Exception Information", padding=10)
            exc_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
            
            exc_text = scrolledtext.ScrolledText(exc_frame, height=8)
            exc_text.pack(fill=tk.BOTH, expand=True)
            exc_text.insert(tk.END, str(thread.exception))
            exc_text.config(state=tk.DISABLED)
            
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
        
    def _show_group_dialog(self, group):
        """Show a dialog with group details"""
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Group Details: {group.name}")
        dialog.geometry("700x500")
        dialog.transient(self.root)
        dialog.grab_set()
        
        # Center on parent
        dialog.geometry("+{}+{}".format(
            self.root.winfo_x() + int(self.root.winfo_width()/2 - 350),
            self.root.winfo_y() + int(self.root.winfo_height()/2 - 250)
        ))
        
        # Group info
        info_frame = ttk.LabelFrame(dialog, text="Group Information", padding=10)
        info_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Create grid for group info
        info_grid = ttk.Frame(info_frame)
        info_grid.pack(fill=tk.X, expand=True)
        
        # Add group properties
        stats = group.get_stats()
        row = 0
        for label, value in [
            ("Name", group.name),
            ("Description", group.description or "No description"),
            ("Created", time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(group.creation_time))),
            ("Thread Count", stats["total"]),
            ("Running", stats["running"]),
            ("Waiting", stats["waiting"]),
            ("Completed", stats["completed"]),
            ("Failed", stats["failed"])
        ]:
            ttk.Label(info_grid, text=f"{label}:", font=('Arial', 10, 'bold')).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_grid, text=str(value)).grid(row=row, column=1, sticky=tk.W, padx=5, pady=2)
            row += 1
            
        # Group threads
        threads_frame = ttk.LabelFrame(dialog, text="Group Threads", padding=10)
        threads_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Thread list with scroll
        columns = ("ID", "Name", "Status", "Priority", "Runtime")
        group_threads_tree = ttk.Treeview(threads_frame, columns=columns, show="headings")
        
        # Configure headings
        for col in columns:
            group_threads_tree.heading(col, text=col)
            
        # Configure column widths
        group_threads_tree.column("ID", width=80)
        group_threads_tree.column("Name", width=150)
        group_threads_tree.column("Status", width=100)
        group_threads_tree.column("Priority", width=100)
        group_threads_tree.column("Runtime", width=100)
        
        # Add vertical scrollbar
        vsb = ttk.Scrollbar(threads_frame, orient="vertical", command=group_threads_tree.yview)
        group_threads_tree.configure(yscrollcommand=vsb.set)
        
        # Pack everything
        vsb.pack(side=tk.RIGHT, fill=tk.Y)
        group_threads_tree.pack(fill=tk.BOTH, expand=True)
        
        # Populate thread list
        for thread in group.threads:
            group_threads_tree.insert("", tk.END, values=(
                thread.thread_id[:8],
                thread.name,
                thread.status.name,
                thread.priority.name,
                f"{thread.get_runtime():.2f}s"
            ))
            
        # Group controls
        control_frame = ttk.Frame(dialog)
        control_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(control_frame, text="Terminate All", command=lambda: self._terminate_group(group, dialog), style="Warning.TButton").pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Refresh", command=lambda: self._refresh_group_dialog(dialog, group, group_threads_tree)).pack(side=tk.LEFT, padx=5)
        
        # Close button
        ttk.Button(dialog, text="Close", command=dialog.destroy).pack(side=tk.RIGHT, padx=10, pady=10)
        
    def _refresh_group_dialog(self, dialog, group, tree):
        """Refresh the group dialog thread list"""
        # Clear the list
        for item in tree.get_children():
            tree.delete(item)
            
        # Populate thread list
        for thread in group.threads:
            tree.insert("", tk.END, values=(
                thread.thread_id[:8],
                thread.name,
                thread.status.name,
                thread.priority.name,
                f"{thread.get_runtime():.2f}s"
            ))
            
    def _pause_thread(self, thread, dialog=None):
        """Pause a thread"""
        if thread.pause():
            self._log_activity(f"Paused thread: {thread.name}")
            self._refresh_threads()
            if dialog:
                dialog.destroy()
                self._show_thread_dialog(thread)
                
    def _resume_thread(self, thread, dialog=None):
        """Resume a thread"""
        if thread.resume():
            self._log_activity(f"Resumed thread: {thread.name}")
            self._refresh_threads()
            if dialog:
                dialog.destroy()
                self._show_thread_dialog(thread)
                
    def _terminate_thread(self, thread, dialog=None):
        """Terminate a thread"""
        thread.terminate()
        self._log_activity(f"Terminated thread: {thread.name}")
        self._refresh_threads()
        if dialog:
            dialog.destroy()
            
    def _terminate_group(self, group, dialog=None):
        """Terminate all threads in a group"""
        result = messagebox.askokcancel("Terminate Group", f"Are you sure you want to terminate all threads in group '{group.name}'?", parent=dialog)
        if result:
            group.terminate_all()
            self._log_activity(f"Terminated all threads in group: {group.name}")
            self._refresh_threads()
            self._refresh_groups()
            if dialog:
                dialog.destroy()
                
    def _set_log_level(self):
        """Set the log level"""
        level_name = self.log_level_var.get()
        level = getattr(logging, level_name, logging.INFO)
        logger.setLevel(level)
        self._log_activity(f"Set log level to {level_name}")
        
    def _clear_log(self):
        """Clear the system log"""
        self.system_log.config(state=tk.NORMAL)
        self.system_log.delete(1.0, tk.END)
        self.system_log.config(state=tk.DISABLED)
        
    def _log_activity(self, message):
        """Log an activity message"""
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        log_message = f"{timestamp} - {message}"
        
        # Add to activity log
        self.activity_log.config(state=tk.NORMAL)
        self.activity_log.insert(tk.END, log_message + "\n")
        self.activity_log.see(tk.END)
        self.activity_log.config(state=tk.DISABLED)
        
        # Add to system log
        self.system_log.config(state=tk.NORMAL)
        self.system_log.insert(tk.END, log_message + "\n")
        self.system_log.see(tk.END)
        self.system_log.config(state=tk.DISABLED)
        
        # Log to logger
        logger.info(message)
        
    # Demo task functions
    def _cpu_bound_task(self, duration):
        """CPU-bound task for testing"""
        start_time = time.time()
        result = 0
        
        while time.time() - start_time < duration:
            # Simulate CPU-intensive work
            for i in range(10000):
                result += i * i
                
        return result
        
    def _io_bound_task(self, duration):
        """IO-bound task for testing"""
        chunks = int(duration)
        
        for i in range(chunks):
            # Simulate IO operation
            time.sleep(1)
            
        return f"Completed {chunks} IO operations"
        
    def _exception_task(self, duration):
        """Task that raises an exception"""
        time.sleep(duration / 2)
        raise ValueError("This is a test exception")
        
    def _random_sleep_task(self, duration):
        """Task with random sleeps"""
        import random
        start_time = time.time()
        sleeps = []
        
        while time.time() - start_time < duration:
            sleep_time = random.uniform(0.1, 0.5)
            time.sleep(sleep_time)
            sleeps.append(sleep_time)
            
        return f"Completed {len(sleeps)} random sleeps"
        
    def _counter_task(self, duration):
        """Simple counter task"""
        count = 0
        end_time = time.time() + duration
        
        while time.time() < end_time:
            count += 1
            time.sleep(0.01)
            
        return f"Counted to {count}"
        
    def run(self):
        """Run the GUI"""
        self.root.protocol("WM_DELETE_WINDOW", self._on_close)
        self.root.mainloop()
        
    def _on_close(self):
        """Handle window close event"""
        # Stop resource tracking
        self.thread_master.stop_resource_tracking()
        
        # Save session log
        self.thread_master.save_session_log()
        
        # Terminate all threads
        self.thread_master.terminate_all()
        
        # Destroy the window
        self.root.destroy()

# Updated by Hasini

# Updated by Hasini

# Commit 5 marker
