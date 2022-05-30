# ViralBERT
Code for our paper:

[ViralBERT: A User Focused BERT-Based Approach to Virality Prediction](https://doi.org/10.1145/nnnnnnn.nnnnnnn) from UMAP 2022

Rikaz Rameez, Hossein A. Rahmani, Emine Yilmaz

## Architecture
![ViralBERT architecture](/images/arch.png)

## Dataset collection
A dataset is needed to train the model - the collection method is in the TwitterDataset folder. 

### Prerequisites
The following is needed to run data collection:
- Python (>=3.6) with pip
- Authorisation to use the Twitter API (can be applied for [here](https://developer.twitter.com/en/apply-for-access))

### Setup
1. Add your Twitter API bearer token and consumer information into the .twitter_keys.yaml file
2. Create a Python [virtual environment](https://docs.python.org/3/library/venv.html) if required
3. Install Python dependencies:
   ```sh
   python3 -m pip install -r requirements.txt
   ```
4. (OPTIONAL) Modify fetch_data.py with the required time interval for collection and number of batches of data to collect
5. Run fetch_data.py
   ```sh
   python3 fetch_data.py
   ```
Within the time interval specified a data batch will be collected

## Modelling
Once datasets are available, the models can be trained

### Prerequisites
The following is needed to run models
- [Conda](https://docs.conda.io/projects/conda/en/latest/user-guide/install/index.html)

### Setup
These instructions may not work for systems not on 64 bit linux. To run on other platforms, install the corresponding platform-specific conda package.

To create a new environment and install the required conda packages:
```sh
conda create --name env --file conda.txt
```

### Dataset preparation
First move dataset files to the same directory as data_prep.ipynb

Follow the cells within this file to save a prepared dataset for model training

### Models
Follow the instructions within the models.ipynb notebook to load the dataset and add labels.

Choose a model under a heading to train and test on the data.

## Contact
TBA

