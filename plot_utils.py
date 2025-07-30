import matplotlib.pyplot as plt

dpi = 1000


def plot_noisy_curve(filename, realcount, realgrid, num, nt):
    name = filename.split(".fits")[0]
    path = f"{name}_{nt}_NOISY.png"
    y_original = [realcount[t] for t in range(0, num)]
    x_vals = [realgrid[t] for t in range(0, num)]

    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, y_original, color="red", label="Original Count")
    plt.xlabel("Time (realgrid)")
    plt.ylabel("Number of Photons")
    plt.title(f"{filename} - N. Bins {nt}")
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()
    return path


def plot_or_vs_opt(filename, realcount, realgrid, num, newarrbin, nt):
    name = filename.split(".fits")[0]
    path = f"{name}_{nt}_TECLA.png"
    y_original = [realcount[t] for t in range(0, num)]
    y_new = [len(newarrbin[t]) for t in range(0, num)]
    x_vals = [realgrid[t] for t in range(0, num)]

    plt.figure(figsize=(10, 6))
    plt.plot(x_vals, y_original, color="red", label="Original Count")
    plt.plot(x_vals, y_new, color="blue", label="Optimized Count")
    plt.xlabel("Time (realgrid)")
    plt.ylabel("Number of Photons")
    plt.title(
        f"Comparison of Original vs Optimized Bin Counts – {filename} N. Bins {nt}"
    )
    plt.grid(True)
    plt.legend()
    plt.tight_layout()
    plt.savefig(path, dpi=dpi)
    plt.close()
    return path
