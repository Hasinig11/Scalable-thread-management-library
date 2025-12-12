# Scalable Thread Management System (ThreadMaster)

## Overview
**ThreadMaster** is a powerful Python library and GUI application designed for efficient thread management, synchronization, and monitoring. It provides a high-level interface for creating managed threads, organizing them into groups, and handling thread pools, all while offering real-time visualization of system resources and thread states.

This project is ideal for understanding operating system concepts like multithreading, race conditions (solved via locks), synchronization primitives (Semaphores, Barriers), and resource management.

## Key Features
- **Visual Dashboard**: Real-time graphs for CPU and Memory usage.
- **Managed Threads**: Create threads with priorities, status tracking (Running, Waiting, Failed), and lifecycle control (Pause, Resume, Terminate).
- **Thread Groups**: Organize related threads and manage them collectively (e.g., terminate an entire group).
- **Thread Pools**: Efficiently execute tasks using a worker pool pattern.
- **Synchronization**: Built-in support for Barriers, Semaphores, and Event Buses.
- **Resource Tracking**: Monitors system performance while threads are active.

## Prerequisites
To run this application, you need **Python 3.x** and the following libraries:

- `tkinter` (usually included with Python)
- `psutil` (for system monitoring)
- `matplotlib` (for graphing)
- `numpy` (dependency for matplotlib)

## Installation

1.  **Clone or Download** this repository.
2.  **Install Dependencies**:
    Open your terminal or command prompt and run:
    ```bash
    pip install psutil matplotlib numpy
    ```
    *(Note: `tkinter` is standard library, but on Linux you might need `sudo apt-get install python3-tk`)*

## Usage

1.  **Run the Application**:
    Navigate to the project directory and execute the main script:
    ```bash
    python main.py
    ```

2.  **Using the Dashboard**:
    - **Dashboard Tab**: View global statistics and system health charts. Click "Create Demo Threads" to see it in action.
    - **Create Tab**: Launch new custom threads. You can choose different types of tasks (CPU Bound, IO Bound, etc.) to see how they affect the system.
    - **Threads Tab**: View details of all active threads. Double-click a thread to pause, resume, or terminate it.
    - **Groups Tab**: Manage thread groups.
    - **System Tab**: Deep dive into system logs and thread pool status.

## Architecture & Concepts

### 1. ThreadMaster (The Engine)
The core class that maintains registries of all threads, groups, and pools. It handles the "heavy lifting" of resource tracking and global cleanup.

### 2. ManagedThread
A wrapper around standard Python `threading.Thread`. It adds:
- **Status**: Pending, Running, Waiting, Completed, Failed, Terminated.
- **Control**: `pause()`, `resume()`, `terminate()`.
- **Identity**: Unique IDs and customizable names.

### 3. ThreadGroup
Allows logical grouping of threads. Useful for "bulk actions" like cancelling a specific operation that involves multiple threads.

### 4. ThreadPoolExecutor
A custom implementation of a thread pool (distinct from `concurrent.futures`). It uses a queue of tasks and a fixed number of worker threads to process them, preventing system overload.

## Troubleshooting
- **Missing tkinter**: If you get an error about `_tkinter`, ensure you have it installed for your Python version.
- **Permission Error**: CPU monitoring `psutil` might require administrative privileges on some strict systems, though usually it runs fine in user mode.

# Updated by Hasini

# Updated by Hasini
