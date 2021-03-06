
# Example 1: Iris

This example demonstrates the end-to-end workflow of a Machine
Learning project that works with tabular data.

All steps required for running this example can be found in its [script](https://github.com/noronha-dataops/noronha/tree/master/examples/1_iris/script.sh).

## Dataset

The dataset used here is [iris](https://en.wikipedia.org/wiki/Iris_flower_data_set), one of the simplest Machine Learning study cases. However, we have separated it in two files: one for the [features](https://github.com/noronha-dataops/noronha/tree/master/examples/iris/datasets/measures.csv) (flower measures) and one for the [labels](https://github.com/noronha-dataops/noronha/tree/master/examples/iris/datasets/species.csv) (flower species). This way we can see how the framework handles tabular datasets that are structured in multiple files.  

## Framework features

Those are the key features demonstrated in this example:

- Structured datasets
- Project building
- In-Notebook shortcuts
- Training and deploying
- Routed inference requests

## Reusability

This example may be reused as a template in other Machine Learning projects that handle tabular data by changing some code snippets in these areas:

- [Project setup and CLI actions](https://github.com/noronha-dataops/noronha/tree/master/examples/iris/script.sh)
    - Model files and dataset files definition
    - Names, descriptions and metadata
- [Training notebook](https://github.com/noronha-dataops/noronha/tree/master/examples/iris/notebooks/train.ipynb)
    - Parameter injection cell
    - Dataset loading cell
    - Training cell
- [Inference notebook](https://github.com/noronha-dataops/noronha/tree/master/examples/iris/notebooks/predict.ipynb)
    - Model loading cell
    - Prediction function

## Next steps

- For further commands and usage options, see the [CLI reference](https://noronha-dataops.readthedocs.io/en/latest/reference/cli.html).

- For a better understanding of the relationships between entities (models, versions, trainings, etc...) see the [data model guide](https://noronha-dataops.readthedocs.io/en/latest/guide/data_model.html).

- For running in a more robust configuration set-up or customizing the framework's behaviour, see the [configuration manual](https://noronha-dataops.readthedocs.io/en/latest/guide/configuration.html). 
