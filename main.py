from subprocess import call
from datetime import datetime, timedelta
import click
import shutil
import glob
import os
import math
import functools

contexts_dir = "/home/santiago/daily-contexts"
date_format = '%Y-%m-%d'
today = datetime.today().date()
today_str = today.strftime(date_format)


def str_to_date(date_str):
  return datetime.strptime(date_str, date_format).date()


def find_context(contexts, id):
  return find_context_by(contexts, 'id', int(id))

def find_context_by(contexts, key, value):
  found = None
  for context in contexts:
    if context[key] == value:
      found = context
      break
  return found

def sort_contexts(contexts):
  return sorted(contexts, key=lambda x: x["date"])

def contexts_paths():
  return glob.glob(f"{contexts_dir}/*.ctx")

def data_from_path(context_path):
  context_file = os.path.basename(context_path)
  date_str, name = context_file[:10], context_file[11:] 
  date = str_to_date(date_str)
  name = name.split(".")[0]

  return {
    "full_path": context_path,
    "filename": context_file,
    "date_str": date_str,
    "date": date,
    "name": name
  } 

@functools.cache
def build_contexts():
  contexts = []
  for path in contexts_paths():
    context_data = data_from_path(path)
    contexts.append(context_data)
  
  for idx, context in enumerate(sort_contexts(contexts)):
    context['id'] = idx + 1

  return contexts 

def list_contexts(begin_date=today, end_date=today):
  contexts = build_contexts()  
  if len(contexts) == 0:
    return []

  result_contexts = sort_contexts(contexts)
  def check_date(context):
    context_date = context['date']
    return begin_date <= context_date <= end_date 

  return list(filter(check_date, result_contexts))

def fsearch(query):
  return build_contexts()

def format_search_result(ctx):
  name = ctx["name"]
  date = ctx["date_str"]
  id = ctx["id"]
  content = open(ctx['full_path'], "r").read()
  content = ''.join(content.splitlines())
  preview = pad_right(content, 30)
  return f"{id}\t{date}\t{preview}\t{name}"

def pad_right(text, count):
  text = text[:count]
  for i in range(count - len(text)):
    text += ' '
  return text

def path_preview(name):
  return f"{contexts_dir}/{today}-{name}.ctx"

def from_today(days):
  delta = timedelta(days=days)
  return today + delta

def open_in_vim(full_path, read_only=False):
  if read_only:
    call(['view', full_path])
    return

  vim_options = "autocmd TextChanged,TextChangedI * silent write |\
                 set autoread | set noswapfile | set nobackup"
  call(['vim', "-c", vim_options, full_path])

### commands

@click.group()
def context():
  pass
 
@click.command(name='alloc')
@click.argument('name', default='root')
def open_command(name):
  context_path = path_preview(name)
  open_in_vim(context_path)

@click.command(name='fsearch')
@click.argument('query', default='')
def fsearch_command(query):
  contexts = fsearch(query)
  for ctx in contexts:
    click.echo(format_search_result(ctx))

@click.command()
@click.option('--max-age', default=math.inf, flag_value=1, is_flag=False,  show_default=True, help="Show contexts from last n days")
@click.option('-sf','show_filenames', is_flag=True)
@click.option('-sn','show_names', is_flag=True)
def ls(max_age, show_filenames, show_names):
  contexts = []
  if max_age == math.inf:
    contexts = sort_contexts(build_contexts())
  else:
    begin_date = from_today(-max_age)
    contexts = list_contexts(begin_date, today) 

  if len(contexts) == 0:
    return

  for context in contexts:
    context_name = context["name"]
    date = context["date_str"]
    id = context["id"]
    output_str = f"{id}\t{date}\t{context_name}"

    if show_filenames:
      output_str = context["filename"]
    elif show_names:
      output_str = context["name"]

    if date == today_str:
      click.secho(output_str, fg='green')
    else:
      click.echo(output_str)

@click.command()
@click.argument('name')
def reuse(name):
  yesterday = from_today(-1)
  yesterday_contexts = list_contexts(yesterday, yesterday)
  context_to_reuse = find_context_by(yesterday_contexts, 'name', name)

  if context_to_reuse is None:
    click.echo(f"Context with name {name} not found")
    return

  old_path = context_to_reuse['full_path']
  new_path = path_preview(name)
  if not os.path.exists(new_path):
    shutil.copyfile(old_path, new_path)

  open_in_vim(new_path)

@click.command()
@click.argument('id')
def view(id):
  contexts = build_contexts()
  found_ctx = find_context(contexts, id)
  if not found_ctx:
    click.echo("Context not found")
    return
  open_in_vim(found_ctx['full_path'], read_only=True)

context.add_command(open_command)
context.add_command(ls)
context.add_command(reuse)
context.add_command(view)
context.add_command(fsearch_command)

if __name__ == '__main__':
    context()
