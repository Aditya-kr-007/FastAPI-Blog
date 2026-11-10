from sqlalchemy import Column,Integer,String,Text,ForeignKey
from sqlalchemy.orm import relationship
from database import Base

#Blog Table
class Blog(Base):
    __tablename__ = "blogs"

    id = Column(Integer, primary_key=True)
    title = Column(String)
    content = Column(Text)
    ownership = relationship("BlogAuthor", uselist=False, cascade="all, delete-orphan", lazy="joined")

    @property
    def owner_id(self):
        return self.ownership.user_id if self.ownership else None

    @property
    def author(self):
        return self.ownership.user.username if self.ownership else "The Margin"


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    username = Column(String(30), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)


class BlogAuthor(Base):
    """Separate ownership table keeps existing blog tables and posts intact."""
    __tablename__ = "blog_authors"
    blog_id = Column(Integer, ForeignKey("blogs.id"), primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User", lazy="joined")
