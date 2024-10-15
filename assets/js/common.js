// function - deploy DP in modal

var cbModal = document.getElementById('cb-modal');
if (typeof(cbModal) != 'undefined' && cbModal != null) {
  var myModal = new bootstrap.Modal(document.getElementById('cb-modal'), {
    backdrop: 'static',
    keyboard: false
  })  
}

function openModal( modalTitle, dataPageSrc ) {
  $( '#cb-modal-body' ).html( '' );
  var dataPageScript = document.createElement("script");
  dataPageScript.src = dataPageSrc;
  document.getElementById( 'cb-modal-body' ).appendChild( dataPageScript );

  $( '#cb-modal-title' ).html( modalTitle );
  myModal.show();
}

// function - get URL Vars
function getUrlVars() {
  var vars = [], hash;
  var hashes = window.location.href.slice(window.location.href.indexOf('?') + 1).split('&');

  for(var i = 0; i < hashes.length; i++)
  {
      hash = hashes[i].split('=');
  hash[1] = unescape(hash[1]);
  vars.push(hash[0]);
      vars[hash[0]] = hash[1];
  }

  return vars;
}
var urlVars = getUrlVars();

// hide default submit button row at the bottom of inline forms
document.addEventListener('DataPageReady', function (event) {
  $( '.cb-hide-submit input[type="submit"]' ).closest( 'tr' ).remove();
  $( '.cb-btn-reset' ).bind( 'click', function() {
    $( this ).closest( 'form' ).find( 'select, input[type="text"]' ).val( '' );
    $( this ).closest( 'form' ).submit();
  });
});