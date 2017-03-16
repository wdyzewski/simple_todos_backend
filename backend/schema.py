from django.db.models import Q
from django.contrib.auth.models import User as UserModel
from django.contrib.auth import authenticate
from django.core.exceptions import PermissionDenied
from graphene_django import DjangoObjectType
import graphene
import datetime
from .models import TaskModel, SessionToken

class Task(DjangoObjectType):
    class Meta:
        model = TaskModel

class User(DjangoObjectType):
    class Meta:
        model = UserModel
        only_fields = ('id', 'username',)

# dummy simple mutation:

class Hello(graphene.Mutation):
    # input fields are in class Input
    class Input:
        name = graphene.String()

    # returned values are class members
    hello_text = graphene.String()

    @staticmethod
    def mutate(root, args, context, info):
        text = "Hello, %s!" % (args.get('name') or 'world')
        return Hello(hello_text=text)

# inspired by: https://github.com/davidyaha/apollo-accounts-server

class CreateAccount(graphene.Mutation):
    class Input:
        username = graphene.String()
        password = graphene.String()
        email    = graphene.String()

    id = graphene.Int()
    username = graphene.String()

    @staticmethod
    def mutate(root, args, context, info):
        user = UserModel.objects.create_user(args.get('username'),
                    args.get('email'), args.get('password'))
        user.save()
        return CreateAccount(id=user.id, username=user.username)

class LoginWithPassword(graphene.Mutation):
    """
    Django sessions are very obvious to use here, but it turns out they are not so easy to use in this case:
    http://stackoverflow.com/questions/235950/how-to-lookup-django-session-for-a-particular-user
    """
    class Input:
        username = graphene.String()
        password = graphene.String()

    user_id = graphene.ID()
    username = graphene.String()
    token = graphene.String()

    @staticmethod
    def mutate(root, args, context, info):
        user = authenticate(username=args.get('username'),
                    password=args.get('password'))
        if user is not None:
            st = SessionToken.create(user)
            st.save()
            return LoginWithPassword(user_id=user.id,
                    username=args.get('username'), token=st.token)
        raise PermissionDenied("Cannot authenticate")

class Logout(graphene.Mutation):
    class Input:
        token = graphene.String()

    ok = graphene.String()

    @staticmethod
    def mutate(root, args, context, info):
        SessionToken.objects.get(token=args.get('token')).delete()
        return Logout(ok='OK')

class AddTask(graphene.Mutation):
    class Input:
        token = graphene.String()
        text = graphene.String()
        checked = graphene.Boolean()
        private = graphene.Boolean()

    task_id = graphene.Int()

    @staticmethod
    def mutate(root, args, context, info):
        task = TaskModel(text=args.get('text'),
                    created_at=datetime.datetime.now(),
                    owner=SessionToken.objects.get(token=args.get('token')).user,
                    checked=args.get('checked') or False,
                    private=args.get('private') or False)
        task.save()
        return AddTask(task_id=task.id)

class DeleteTask(graphene.Mutation):
    class Input:
        token = graphene.String()
        task_id = graphene.Int()

    ok = graphene.String()

    @staticmethod
    def mutate(root, args, context, info):
        task = TaskModel.objects.get(id=args.get('task_id'),
                    owner=SessionToken.objects.get(token=args.get('token')).user)
        task.delete()
        return DeleteTask(ok='OK')

class ToggleChecked(graphene.Mutation):
    class Input:
        token = graphene.String()
        task_id = graphene.Int()

    checked = graphene.Boolean()

    @staticmethod
    def mutate(root, args, context, info):
        task = TaskModel.objects.get(id=args.get('task_id'),
                    owner=SessionToken.objects.get(token=args.get('token')).user)
        task.checked = not task.checked
        task.save()
        return ToggleChecked(checked=task.checked)

class TogglePrivate(graphene.Mutation):
    class Input:
        token = graphene.String()
        task_id = graphene.Int()

    private = graphene.Boolean()

    @staticmethod
    def mutate(root, args, context, info):
        task = TaskModel.objects.get(id=args.get('task_id'),
                    owner=SessionToken.objects.get(token=args.get('token')).user)
        task.private = not task.private
        task.save()
        return TogglePrivate(private=task.private)

class MyMutations(graphene.ObjectType):
    # FIXME should be splitted into classes and used inheritance
    hello = Hello.Field()
    create_account = CreateAccount.Field()
    login_with_password = LoginWithPassword.Field()
    logout = Logout.Field()
    add_task = AddTask.Field()
    delete_task = DeleteTask.Field()
    toggle_checked = ToggleChecked.Field()
    toggle_private = TogglePrivate.Field()

class Query(graphene.ObjectType):
    # FIXME should be splitted into classes and used inheritance
    # object_name = return_type
    tasks = graphene.List(Task,
                id=graphene.Int(),
                token=graphene.String())
    users = graphene.List(User)
    hello = graphene.Field(graphene.String,
                name=graphene.String(),
                greeting=graphene.String(),
                token=graphene.String())

    def resolve_tasks(self, args, context, info):
        if args.get('id'):
            # filter, not get! must return List/QuerySet not single object
            return TaskModel.objects.filter(id=args.get('id'))
        # uncomment if you want filtering using Django context from HttpRequest
        #if context.user.is_authenticated():
        #    return TaskModel.objects.filter(Q(owner=context.user) | Q(private=False))
        if args.get('token'):
            try:
                owner = SessionToken.objects.get(token=args.get('token')).user
            except:
                owner = -1
            return TaskModel.objects.filter(Q(owner=owner) | Q(private=False))
        return TaskModel.objects.filter(private=False)

    # missing resolve_users (intended)

    def resolve_hello(self, args, context, info):
        try:
            username = SessionToken.objects.get(token=args.get('token')).user.username
        except:
            username = None
        return '%s, %s! Nice query!' % \
            (args.get('greeting') or 'Hello', username or args.get('name') or 'world')

schema = graphene.Schema(query=Query, mutation=MyMutations)
