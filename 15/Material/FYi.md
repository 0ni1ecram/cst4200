Your Task Manager screenshot shows Python using 77.3% CPU for two common reasons on Windows: either torch.cuda.is_available() silently returned False (falling back to CPU), or CPU preprocessing (num_workers=0 + OpenCV + Matplotlib) is pegging your processor while feeding the GPU.

1. Check If PyTorch Is Actually Using Your GPU

Run this 3-line check in a new notebook cell right now:
python
import torch
print("CUDA available:", torch.cuda.is_available())
print("Active Device :", DEVICE)
print("GPU Name      :", torch.cuda.get_device_name(0) if torch.cuda.is_available() else "NONE (Running on CPU!)")
Use code with caution.
• If it prints CUDA available: False: You have the CPU-only version of PyTorch installed (which pip install torch installs by default on Windows unless you specify the CUDA index URL). Every tensor in your script fell back to DEVICE = "cpu", causing that 77.3% CPU spike.
	• Fix: Reinstall PyTorch with CUDA support in your terminal/Anaconda prompt, then restart your notebook kernel:bash
pip uninstall -y torch torchvision
pip install torch torchvision --index-url https://pytorch.org
Use code with caution.

2. Why CPU Still Spikes Even When the GPU Is Active

If CUDA available is True, your GPU is doing the neural network math, while your CPU hits ~70–80% because:
• num_workers=0 runs data loading on the main CPU thread: Every image read (cv2.imread), resize, normalization, and distance transform (cv2.distanceTransform) runs sequentially on your CPU before sending tensors to the GPU.
• Windows Task Manager hides GPU Compute by default: In Windows Task Manager, the standard GPU column often shows 0% for PyTorch because it only tracks 3D graphics rendering—not CUDA / Compute.
	• How to see real GPU usage: Open Task Manager → Performance tab → click your GPU → change one of the graph dropdowns from 3D to Compute_0 or Cuda (or run nvidia-smi in your terminal).
If you run that 3-line check and share what CUDA available and GPU Name print, I can confirm whether you need the CUDA PyTorch reinstall or if your GPU is already active!
----------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
That warning confirms it: PyTorch is running on your CPU because the CPU-only build of PyTorch is installed (no accelerator is found), which explains why Python hit 77.3% CPU in Task Manager.

How to Enable Your NVIDIA GPU in 2 Steps


Step 1: Verify Your GPU Driver & CUDA Version

Open Command Prompt or Anaconda Prompt and run:
bash
nvidia-smi
Use code with caution.
(If nvidia-smi shows your NVIDIA GPU and a CUDA version like 12.x or 13.x at the top right, your driver is ready. If you have an Intel/AMD integrated GPU rather than an NVIDIA card, PyTorch CUDA won't run on it.)

Step 2: Install the CUDA-Enabled PyTorch Build

In the same terminal/Anaconda Prompt (make sure your Jupyter virtual environment is activated), uninstall the CPU-only version and install the GPU build:
bash
pip uninstall -y torch torchvision
pip install torch torchvision --index-url https://pytorch.org
Use code with caution.
(If cu124 gives a version mismatch with an older GPU, use --index-url https://pytorch.org instead.)

Step 3: Restart Kernel & Verify

1. In Jupyter Notebook, click Kernel → Restart Kernel.
2. Run this check:python
import torch
print("CUDA available:", torch.cuda.is_available())
print("GPU Name      :", torch.cuda.get_device_name(0))
Use code with caution.
Once CUDA available: True prints, your existing training and tiled inference scripts will automatically route to your GPU (DEVICE = "cuda"), drop your CPU usage, and train 10x–20x faster.
If you run nvidia-smi and want to share your GPU model (or if you're using an AMD/Intel GPU instead of NVIDIA), let me know and I'll give you the exact command for your hardware.
-------------------------------------------------------------------------------------------------------------------------------------------------------