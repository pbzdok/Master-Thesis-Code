import os

import numpy as np
import pandas as pd
import skimage
import sklearn.metrics
import streamlit as st
import torch
import torchvision
import torchxrayvision as xrv

transform = torchvision.transforms.Compose([xrv.datasets.XRayCenterCrop(),
                                            xrv.datasets.XRayResizer(224)])


@st.cache
def load_nih_dataset():
    d_nih = xrv.datasets.NIH_Dataset(imgpath='./data/NIH/images-224',
                                     csvpath='./data/NIH/Data_Entry_2017.csv',
                                     transform=transform)
    xrv.datasets.relabel_dataset(xrv.datasets.default_pathologies, d_nih)
    return d_nih


@st.cache
def load_rsna_dataset():
    d_rsna = xrv.datasets.RSNA_Pneumonia_Dataset(imgpath='./data/kaggle-pneumonia-jpg/stage_2_train_images_jpg',
                                                 views=["PA", "AP"],
                                                 unique_patients=True,
                                                 transform=transform)
    return d_rsna


@st.cache
def load_detailed_rsna_class_info():
    return pd.read_csv('./data/kaggle-pneumonia-jpg/stage_2_detailed_class_info.csv')


@st.cache
def load_cluster_metadata():
    return pd.read_csv('./data/kaggle-pneumonia-jpg/metadata_with_clusters.csv')


@st.cache
def calculate_cluster_metrics(clusters):
    anomaly_score = np.empty([6, 1])
    mean_age = np.empty([6, 1])
    max_age = np.empty([6, 1])
    min_age = np.empty([6, 1])
    n_men = np.empty([6, 1])
    n_women = np.empty([6, 1])
    n_pathological_cluster = np.empty([6, 1])
    n_non_pathological_cluster = np.empty([6, 1])

    for i, c in clusters:
        anomaly_score[i] = c['anomaly_score'].mean()
        mean_age[i] = c['PatientAge'].mean()
        max_age[i] = c['PatientAge'].max()
        min_age[i] = c['PatientAge'].min()
        n_men[i] = sum(c['PatientSex'] == 'M')
        n_women[i] = sum(c['PatientSex'] == 'F')
        n_pathological_cluster[i] = sum(c['Target'] == 1)
        n_non_pathological_cluster[i] = sum(c['Target'] == 0)

    return {
        'anomaly': anomaly_score,
        'mean_age': mean_age,
        'max_age': max_age,
        'min_age': min_age,
        'n_men': n_men,
        'n_women': n_women,
        'n_path': n_pathological_cluster,
        'n_non_path': n_non_pathological_cluster
    }


def calculate_rsna_metrics(model, dataset, force=False):
    path = './data/kaggle-pneumonia-jpg/predictions.csv'
    if os.path.isfile(path) and not force:
        df = pd.read_csv(path)
    else:
        ids = []
        y_true = []
        y_pred = []
        with torch.no_grad():
            for i in np.random.randint(0, len(dataset), 1000):
                sample = dataset[i]
                ids.append(dataset.csv['patientId'][sample['idx']])
                y_true.append(sample["lab"][0])
                out = model(torch.from_numpy(sample["img"]).unsqueeze(0)).cpu()
                out = torch.sigmoid(out)
                out = (out > 0.66).float()
                out = out.detach().numpy()[0]
                out = out[8]
                print(out)
                y_pred.append(out)

        df = pd.DataFrame({
            'patientid': ids,
            'y_true': y_true,
            'y_pred': y_pred,
        })
        df.to_csv(path)

    accuracy = sklearn.metrics.accuracy_score(df['y_true'], df['y_pred'])
    precision = sklearn.metrics.precision_score(df['y_true'], df['y_pred'])
    recall = sklearn.metrics.recall_score(df['y_true'], df['y_pred'])
    f1 = sklearn.metrics.f1_score(df['y_true'], df['y_pred'])

    result = {
        'accuracy': accuracy,
        'precision': precision,
        'recall': recall,
        'f1': f1
    }

    return df, result


def image_preprocessing(img_path):
    img = skimage.io.imread(img_path)
    img = xrv.datasets.normalize(img, 255)

    # Check that images are 2D arrays
    if len(img.shape) > 2:
        img = img[:, :, 0]
    if len(img.shape) < 2:
        print("error, dimension lower than 2 for image")

    # Add color channel
    img = img[None, :, :]

    return transform(img)
