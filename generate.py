import sys

from crossword import *
import copy

class CrosswordCreator():

    def __init__(self, crossword):
        """
        Create new CSP crossword generate.
        """
        self.crossword = crossword
        self.domains = {
            var: self.crossword.words.copy()
            for var in self.crossword.variables
        }

    def letter_grid(self, assignment):
        """
        Return 2D array representing a given assignment.
        """
        letters = [
            [None for _ in range(self.crossword.width)]
            for _ in range(self.crossword.height)
        ]
        for variable, word in assignment.items():
            direction = variable.direction
            for k in range(len(word)):
                i = variable.i + (k if direction == Variable.DOWN else 0)
                j = variable.j + (k if direction == Variable.ACROSS else 0)
                letters[i][j] = word[k]
        return letters

    def print(self, assignment):
        """
        Print crossword assignment to the terminal.
        """
        letters = self.letter_grid(assignment)
        for i in range(self.crossword.height):
            for j in range(self.crossword.width):
                if self.crossword.structure[i][j]:
                    print(letters[i][j] or " ", end="")
                else:
                    print("█", end="")
            print()

    def save(self, assignment, filename):
        """
        Save crossword assignment to an image file.
        """
        from PIL import Image, ImageDraw, ImageFont
        cell_size = 100
        cell_border = 2
        interior_size = cell_size - 2 * cell_border
        letters = self.letter_grid(assignment)

        # Create a blank canvas
        img = Image.new(
            "RGBA",
            (self.crossword.width * cell_size,
             self.crossword.height * cell_size),
            "black"
        )
        font = ImageFont.truetype("assets/fonts/OpenSans-Regular.ttf", 80)
        draw = ImageDraw.Draw(img)

        for i in range(self.crossword.height):
            for j in range(self.crossword.width):

                rect = [
                    (j * cell_size + cell_border,
                     i * cell_size + cell_border),
                    ((j + 1) * cell_size - cell_border,
                     (i + 1) * cell_size - cell_border)
                ]
                if self.crossword.structure[i][j]:
                    draw.rectangle(rect, fill="white")
                    if letters[i][j]:
                        w, h = draw.textsize(letters[i][j], font=font)
                        draw.text(
                            (rect[0][0] + ((interior_size - w) / 2),
                             rect[0][1] + ((interior_size - h) / 2) - 10),
                            letters[i][j], fill="black", font=font
                        )

        img.save(filename)

    def solve(self):
        """
        Enforce node and arc consistency, and then solve the CSP.
        """
        self.enforce_node_consistency()
        self.ac3()
        return self.backtrack(dict())

    def enforce_node_consistency(self):
        """
        Update `self.domains` such that each variable is node-consistent.
        (Remove any values that are inconsistent with a variable's unary
         constraints; in this case, the length of the word.)
        """
        variables= self.domains.keys()
        for variable in variables:
            l=variable.length
            words=copy.deepcopy(self.domains[variable])
            for world in words:
                if not(len(world)==l):
                    self.domains[variable].remove(world)


    def revise(self, x, y):
        """
        Make variable `x` arc consistent with variable `y`.
        To do so, remove values from `self.domains[x]` for which there is no
        possible corresponding value for `y` in `self.domains[y]`.

        Return True if a revision was made to the domain of `x`; return
        False if no revision was made.
        """
        v=self.crossword.overlaps[x,y]
        revised=False
        words=copy.deepcopy(self.domains[x])
        if v:
            for world1 in words:
                check=True

                for world2 in self.domains[y]:
                    if not(world1[v[0]]==world2[v[1]]):
                        check=False
                        revised=True
                if check:
                    self.domains[x].remove(world1)
        return revised

    def ac3(self, arcs=None):
        """
        Update `self.domains` such that each variable is arc consistent.
        If `arcs` is None, begin with initial list of all arcs in the problem.
        Otherwise, use `arcs` as the initial list of arcs to make consistent.

        Return True if arc consistency is enforced and no domains are empty;
        return False if one or more domains end up empty.
        """
        if not(arcs):
            arcs=list()
            for x in self.domains.keys():
                for y in self.domains.keys():
                    if not(x==y) and self.crossword.overlaps[x,y] :
                        arcs.append((x,y))
        while len(arcs):
            (X,Y)=arcs.pop(0)
            if self.revise(X,Y):
                if len(self.domains[X])==0:
                    return False
                for Z in self.crossword.neighbors(X):
                    if not(Z==Y):
                        arcs.append((Z,X))
        return True



    def assignment_complete(self, assignment):
        """
        Return True if `assignment` is complete (i.e., assigns a value to each
        crossword variable); return False otherwise.
        """
        for  variable in self.domains.keys():
            if variable not in assignment.keys():
                return False
        return True

    def consistent(self, assignment):
        """
        Return True if `assignment` is consistent (i.e., words fit in crossword
        puzzle without conflicting characters); return False otherwise.
        """
        for variable in assignment.keys():
            if not(len(assignment[variable])==variable.length):
                return False
            for Y in self.crossword.neighbors(variable):
                if Y in assignment.keys():
                    v=self.crossword.overlaps[variable,Y]
                    if not( assignment[variable][v[0]] == assignment[Y][v[1]] ):
                        return False

        if not (len(assignment.values())==len(set(assignment.values()))):
            return False
        return True




    def order_domain_values(self, var, assignment):
        """
        Return a list of values in the domain of `var`, in order by
        the number of values they rule out for neighboring variables.
        The first value in the list, for example, should be the one
        that rules out the fewest values among the neighbors of `var`.
        """
        mesure=list()
        for world in self.domains[var]:
            n=0
            for Y in self.crossword.neighbors(var):
                if Y in assignment.keys():
                        continue

                (i,j)=self.crossword.overlaps[var,Y]
                for world2 in self.domains[Y]:
                    if not(world[i]==world2[j]):
                        n+=1
            mesure.append((world,n))
        mesure=sorted(mesure, key=lambda weight: weight[1])
        l=[x[0] for x in mesure]
        return l

    def select_unassigned_variable(self, assignment):
        """
        Return an unassigned variable not already part of `assignment`.
        Choose the variable with the minimum number of remaining values
        in its domain. If there is a tie, choose the variable with the highest
        degree. If there is a tie, any of the tied variables are acceptable
        return values.
        """
        variables=set(self.domains.keys())
        assigned=set(assignment.keys())
        unassigned=variables.difference(assigned)
        u=list()
        for Y in unassigned:
            u.append((Y,len(self.domains[Y])))

        s=sorted(u, key=lambda weight: weight[1])
        value=list()
        for i in range(len(s)) :
            if s[i][1]==s[0][1]:
                value.append(s[i][0])
            else:
                break
        u=list()
        for X in value:
            u.append((X,len(self.crossword.neighbors(X))))
        return sorted(u, key=lambda weight: weight[1])[-1][0]


    def backtrack(self, assignment):
        """
        Using Backtracking Search, take as input a partial assignment for the
        crossword and return a complete assignment if possible to do so.

        `assignment` is a mapping from variables (keys) to words (values).

        If no assignment is possible, return None.
        """
        if self.assignment_complete(assignment):
            return assignment
        var=self.select_unassigned_variable(assignment)
        values=self.order_domain_values(var,assignment)
        for v in values:
            assignment[var]=v
            if self.consistent(assignment):
                result=self.backtrack(assignment)
                if not(result==None):
                    return result
            assignment.pop(var)
        return None

def main():

    # Check usage
    if len(sys.argv) not in [3, 4]:
        sys.exit("Usage: python generate.py structure words [output]")

    # Parse command-line arguments
    structure = sys.argv[1]
    words = sys.argv[2]
    output = sys.argv[3] if len(sys.argv) == 4 else None

    # Generate crossword
    crossword = Crossword(structure, words)
    creator = CrosswordCreator(crossword)
    assignment = creator.solve()

    # Print result
    if assignment is None:
        print("No solution.")
    else:
        creator.print(assignment)
        if output:
            creator.save(assignment, output)


if __name__ == "__main__":
    main()
