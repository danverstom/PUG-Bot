import matplotlib.pyplot as plt
from io import BytesIO
from discord import File

plt.style.use('dark_background')


def my_autopct(pct):
    return ('%.2f' % pct) if pct > 10 else ''


def pie_chart(labels, sizes, explode, title):
    data_stream = BytesIO()
    # Pie chart, where the slices will be ordered and plotted counter-clockwise:
    fig1, ax1 = plt.subplots()
    plt.rcParams['font.size'] = 18
    ax1.pie(sizes, labels=labels, startangle=90)
    ax1.axis('equal')  # Equal aspect ratio ensures that pie is drawn as a circle.
    plt.suptitle(title)
    plt.savefig(data_stream, format='png', bbox_inches="tight", dpi=65, transparent=True)
    plt.close()
    return data_stream


def file_from_data_stream(data_stream):
    chart_file = File(data_stream, filename="pie_chart.png")
    data_stream.seek(0)
