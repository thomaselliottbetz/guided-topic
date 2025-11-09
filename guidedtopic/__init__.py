from logging.config import dictConfig
from typing import Type

from flask import Flask

from guidedtopic.config import Config, configure_logging
from guidedtopic.extensions import init_app as init_extensions


def create_app(config_class: Type[Config] = Config) -> Flask:
    """Application factory for the Guided Topic platform."""

    dictConfig(configure_logging())

    app = Flask(
        __name__,
        template_folder="templates",
        static_folder="static",
    )
    app.config.from_object(config_class)

    init_extensions(app)

    from guidedtopic.main.routes import main
    from guidedtopic.posts.routes import posts
    from guidedtopic.users.routes import users
    from guidedtopic.videos.routes import videos
    from guidedtopic.qna.routes import qna
    from guidedtopic.errors.handlers import errors

    app.register_blueprint(main)
    app.register_blueprint(posts)
    app.register_blueprint(users)
    app.register_blueprint(videos)
    app.register_blueprint(qna)
    app.register_blueprint(errors)

    return app
