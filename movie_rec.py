# Movie Recommender Semester Project for
# Machine Learning at UTSA Computer Science
# Josh Greene

# The blog post below was used as a jumping off point for the project
# https://towardsdatascience.com/the-4-recommendation-engines-that-can-predict-your-movie-tastes-109dc4e10c52
# Code to slide the predictions generated by model.fit was taken from the blog.
# Formatted Movie Lens data was taken from the blog.

import math
import numpy as np
import pandas as pd
import tensorflow as tf
from keras.callbacks import Callback, EarlyStopping, ModelCheckpoint
from keras.layers import (
    Embedding,
    Reshape,
    multiply,
    average,
    dot,
    concatenate,
    merge,
    Input,
    Dense,
)
from keras.models import Model, Sequential


# Set up global variables

data_path = "./data/"
# dataset = "movielens_100k"
dataset = "movielens_1m"

full_dataset_path = data_path + dataset + "/"

# place holder variables for Movie Lens data
ratings = 0
movies = 0
users = 0

TEST_USER = 2000  # A random test user (user_id = 2000)
max_userid = 0
max_movieid = 0

# hyperparameters to test for the project
embedding_sizes = [50, 100]  # The number of dimensional embeddings for movies and users

merge_types = [
    "concatenate",
    "multiply",
    "average",
    "dot",
]

layer_sizes = [[64, 32, 1], [32, 16, 1]]

epochs = 30


# load and prepare the dataset files
def load_data(dataset_path):
    global max_userid
    global max_movieid
    global ratings
    global users
    global movies

    # load the raw ratings data
    ratings = pd.read_csv(
        full_dataset_path + "ratings.csv",
        sep="\t",
        encoding="latin-1",
        usecols=["user_id", "movie_id", "user_emb_id", "movie_emb_id", "rating"],
    )

    # get the number of users
    max_userid = ratings["user_id"].drop_duplicates().max()

    # get the number of movies
    max_movieid = ratings["movie_id"].drop_duplicates().max()

    # create training set
    shuffled_ratings = ratings.sample(frac=1.0, random_state=1)

    # load the user data
    users = pd.read_csv(
        full_dataset_path + "users.csv",
        sep="\t",
        encoding="latin-1",
        usecols=["user_id", "gender", "zipcode", "age_desc", "occ_desc"],
    )

    # load the movie data
    movies = pd.read_csv(
        full_dataset_path + "movies.csv",
        sep="\t",
        encoding="latin-1",
        usecols=["movie_id", "title", "genres"],
    )

    # Shuffling users
    Users = shuffled_ratings["user_emb_id"].values
    print("Users:", Users, ", shape =", Users.shape)

    # Shuffling movies
    Movies = shuffled_ratings["movie_emb_id"].values
    print("Movies:", Movies, ", shape =", Movies.shape)

    # Shuffling ratings
    Ratings = shuffled_ratings["rating"].values
    print("Ratings:", Ratings, ", shape =", Ratings.shape)

    return [Users, Movies], Ratings


def run_experiment(X, y):
    global merge_types
    global embedding_sizes
    global layer_sizes
    global epochs
    global callbacks

    # test out all the merge layer types
    for merge_type in merge_types:

        # test out all the embedding sizes
        for embedding_size in embedding_sizes:

            # test out all the dense layer sizes
            for layers in layer_sizes:

                # build model name for saved file
                model_name = merge_type + "_" + str(embedding_size)

                for num in layers:
                    model_name = model_name + "_" + str(num)

                model_name = model_name + ".h5"

                callbacks = [
                    EarlyStopping("val_loss", patience=2),
                    ModelCheckpoint(model_name, save_best_only=True),
                ]

                model = build_model(merge_type, layers, embedding_size)

                model.compile(loss="mse", optimizer="adamax")

                # Use 30 epochs, 90% training data, 10% validation data
                history = model.fit(
                    X,
                    y,
                    epochs=epochs,
                    validation_split=0.1,
                    verbose=2,
                    callbacks=callbacks,
                )

                # Show the best validation RMSE
                min_val_loss, idx = min(
                    (val, idx) for (idx, val) in enumerate(history.history["val_loss"])
                )

                print(
                    "Minimum RMSE at epoch",
                    "{:d}".format(idx + 1),
                    "=",
                    "{:.4f}".format(math.sqrt(min_val_loss)),
                )

                trained_model = build_model(merge_type, layers, embedding_size)
                trained_model.load_weights(model_name)

                get_user_top20(trained_model)

                get_user_prediction(trained_model)


def build_model(merge_type, dense_layers, embedding_size):
    global max_userid
    global max_movieid

    print("build_model: {0}, {1}".format(merge_type, dense_layers))

    first_input = Input(shape=(1,))
    first_embed = Embedding(max_userid, embedding_size, input_length=1)(first_input)

    second_input = Input(shape=(1,))
    second_embed = Embedding(max_movieid, embedding_size, input_length=1)(second_input)

    if merge_type == "concatenate":
        x = concatenate([first_embed, second_embed])
    elif merge_type == "multiply":
        x = multiply([first_embed, second_embed])
    elif merge_type == "average":
        x = average([first_embed, second_embed])
    elif merge_type == "dot":
        x = dot([first_embed, second_embed], axes=1)

    for layer_size in dense_layers:
        x = Dense(layer_size)(x)

    model = Model(inputs=[first_input, second_input], outputs=x)

    print("\nModel Summary\n")
    print(model.summary())

    return model


def predict_rating(trained_model, user_id, movie_id):
    return trained_model.predict([np.array([user_id - 1]), np.array([movie_id - 1])])[
        0
    ][0]


def get_user_top20(trained_model):
    global ratings

    user_ratings = ratings[ratings["user_id"] == TEST_USER][
        ["user_id", "movie_id", "rating"]
    ]
    user_ratings["prediction"] = user_ratings.apply(
        lambda x: predict_rating(trained_model, TEST_USER, x["movie_id"]), axis=1
    )

    print("\nDisplay Predicted User Ratings and Actual Ratings\n")
    print(
        user_ratings.sort_values(by="rating", ascending=False)
        .merge(movies, on="movie_id", how="inner", suffixes=["_u", "_m"])
        .head(20)
    )


def get_user_prediction(trained_model):
    user_ratings = ratings[ratings["user_id"] == TEST_USER][
        ["user_id", "movie_id", "rating"]
    ]

    user_ratings["prediction"] = user_ratings.apply(
        lambda x: predict_rating(trained_model, TEST_USER, x["movie_id"]), axis=1
    )

    recommendations = ratings[
        ratings["movie_id"].isin(user_ratings["movie_id"]) == False
    ][["movie_id"]].drop_duplicates()

    recommendations["prediction"] = recommendations.apply(
        lambda x: predict_rating(trained_model, TEST_USER, x["movie_id"]), axis=1
    )

    print("\nDisplay Predicted User Ratings for Recommendation\n")
    print(
        recommendations.sort_values(by="prediction", ascending=False)
        .merge(movies, on="movie_id", how="inner", suffixes=["_u", "_m"])
        .head(20)
    )


X, y = load_data(full_dataset_path)

run_experiment(X, y)
