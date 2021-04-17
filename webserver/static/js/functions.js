function enterElement(element) {
    anime.remove(element);
    anime({
        targets: element,
        scale: 1.1,
        duration: 500,
        easing: "easeOutExpo"
    });
};

function leaveElement(element) {
    anime.remove(element);
    anime({
        targets: element,
        scale: 1,
        duration: 500,
        easing: "easeOutExpo"
    });
};

function addGrowingEvents(){
    var elements = document.querySelectorAll('.grow-on-hover');  // Select elements with animated button class

    for (var i = 0; i < elements.length; i++) {
        // Loop through all the elements on the web page and add their event listeners

        // Adding "mouse enter" event listener
        elements[i].addEventListener('mouseenter', function(e) {
            enterElement(e.target);
        }, false);

        // Adding "mouse leave" event listener
        elements[i].addEventListener('mouseleave', function(e) {
            leaveElement(e.target)
        }, false);
    }
}

function main(){
    addGrowingEvents()
}

document.addEventListener("DOMContentLoaded", main);