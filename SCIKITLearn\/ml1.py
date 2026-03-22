import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import sklearn.linear_model
from pathlib import Path
from urllib.request import urlretrieve

def prepare_country_stats(oecd_bli, gdp_per_capita):
    # Keep total inequality rows only
    oecd_bli = oecd_bli[oecd_bli["INEQUALITY"] == "TOT"]

    # One row per country, one column per indicator
    oecd_bli = oecd_bli.pivot(index="Country", columns="Indicator", values="Value")

    # Normalize GDP column name and index
    gdp_per_capita = gdp_per_capita.rename(columns={"2015": "GDP per capita"})
    gdp_per_capita = gdp_per_capita.set_index("Country")

    # Merge OECD + GDP data
    full_country_stats = pd.merge(
        left=oecd_bli,
        right=gdp_per_capita,
        left_index=True,
        right_index=True
    )

    # Sort and return relevant columns
    full_country_stats = full_country_stats.sort_values(by="GDP per capita")
    return full_country_stats[["GDP per capita", "Life satisfaction"]]


def ensure_datasets(data_dir):
    data_dir.mkdir(parents=True, exist_ok=True)

    files_and_urls = {
        "oecd_bli_2015.csv": [
            "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/lifesat/oecd_bli_2015.csv",
            "https://raw.githubusercontent.com/ageron/handson-ml2/master/datasets/lifesat/oecd_bli_2015.csv",
        ],
        "gdp_per_capita.csv": [
            "https://raw.githubusercontent.com/ageron/handson-ml/master/datasets/lifesat/gdp_per_capita.csv",
            "https://raw.githubusercontent.com/ageron/handson-ml2/master/datasets/lifesat/gdp_per_capita.csv",
        ],
    }

    for filename, urls in files_and_urls.items():
        path = data_dir / filename
        if path.exists() and path.stat().st_size > 0:
            continue

        last_error = None
        for url in urls:
            try:
                print(f"Downloading {filename}...")
                urlretrieve(url, path)
                if path.stat().st_size > 0:
                    print(f"Saved: {path}")
                    last_error = None
                    break
            except Exception as e:
                last_error = e

        if last_error is not None:
            raise RuntimeError(f"Could not download {filename}: {last_error}")


# Load the data
data_dir = Path(__file__).resolve().parent / "Datasets"
ensure_datasets(data_dir)
oecd_bli = pd.read_csv(data_dir / "oecd_bli_2015.csv", thousands=',')
gdp_per_capita = pd.read_csv(
    data_dir / "gdp_per_capita.csv",
    thousands=',',
    delimiter='\t',
    encoding='latin1',
    na_values="n/a"
)


# prepare the data
country_stats = prepare_country_stats(oecd_bli, gdp_per_capita)
x = np.c_[country_stats["GDP per capita"]]
y = np.c_[country_stats["Life satisfaction"]]

# Visualize the data
country_stats.plot(kind='scatter', x="GDP per capita", y='Life satisfaction')
plt.show()

# Select a linear model
model = sklearn.linear_model.LinearRegression()

# Train the model
model.fit(x, y)

# Make a prediction for Cyprus
X_new = [[22587]]  # Cyprus' GDP per capita
print(model.predict(X_new))  # outputs [[5.96242338]]
