{

    document.getElementById('toggleMembers').addEventListener('click', function() {
      var memberList = document.getElementById('memberList');
      if (memberList.style.display === 'none') {
          memberList.style.display = 'block';
          this.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-down-fill" viewBox="0 0 16 16"><path d="M7.247 11.14 2.451 5.658C1.885 5.013 2.345 4 3.204 4h9.592a1 1 0 0 1 .753 1.659l-4.796 5.48a1 1 0 0 1-1.506 0z"/></svg>';
      } else {
          memberList.style.display = 'none';
          this.innerHTML = '<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" fill="currentColor" class="bi bi-caret-right-fill" viewBox="0 0 16 16"><path d="m12.14 8.753-5.482 4.796c-.646.566-1.658.106-1.658-.753V3.204a1 1 0 0 1 1.659-.753l5.48 4.796a1 1 0 0 1 0 1.506z"/></svg>';
      }
    });


  tippy('#add-participant', {
    content: modal,
    placement: 'bottom-end',
    arrow: false,
    theme: 'light',
    trigger: 'click',
    interactive: true,
    allowHTML: true,
  });

}