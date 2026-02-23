factorial(0, 1). % Base case: factorial of 0 is 1

factorial(N, Result) :-
    N > 0, % Ensure N is positive
    N1 is N - 1, % Calculate N-1
    factorial(N1, Result1), % Recursively calculate factorial of N-1
    Result is N * Result1. % Calculate factorial of N

% Query examples:
% factorial(0, F).
% factorial(5, F).