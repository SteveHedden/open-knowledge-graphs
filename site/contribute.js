(() => {
  const dialog = document.getElementById('contribute-dialog');
  const trigger = document.getElementById('contribute-button');
  trigger.addEventListener('click', () => {
    dialog.showModal();
    dialog.scrollTop = 0;
    document.getElementById('contribute-title').focus({preventScroll:true});
  });
  dialog.addEventListener('close', () => trigger.focus({preventScroll:true}));
  document.getElementById('project-request-form').addEventListener('submit', (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    if (!form.reportValidity()) return;
    const fields = new FormData(form);
    const body = [
      '### Project name', fields.get('project').trim(),
      '### Website or repository', fields.get('website').trim(),
      '### What should we add or change?', fields.get('change').trim(),
      '### Wikidata link (optional)', fields.get('wikidata').trim() || 'Not provided',
    ].join('\n\n');
    const url = new URL('https://github.com/SteveHedden/open-knowledge-graphs/issues/new');
    url.searchParams.set('title', `Project request: ${fields.get('project').trim()}`);
    url.searchParams.set('body', body);
    window.open(url.href, '_blank', 'noopener,noreferrer');
  });
})();
